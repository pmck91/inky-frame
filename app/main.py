from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .image_ops import save_original_upload, save_processed_canvas_png
from .scheduler import RotationScheduler
from .storage import (
    add_pending_image,
    delete_image,
    get_display_size,
    get_image,
    get_images_sorted,
    get_next_pending_image,
    get_pending_images,
    get_rotation_seconds,
    mark_image_ready,
    reorder_images,
    set_display_size,
    set_rotation_seconds,
)

app = FastAPI(title="eInk Photo Frame")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/data", StaticFiles(directory="data", check_dir=False), name="data")
templates = Jinja2Templates(directory="templates")
scheduler = RotationScheduler()


@app.on_event("startup")
async def startup_event() -> None:
    scheduler.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await scheduler.stop()


@app.get("/")
async def index(request: Request):
    images = get_images_sorted()
    pending = get_pending_images()
    display_width, display_height = get_display_size()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "images": images,
            "pending": pending,
            "pending_count": len(pending),
            "rotation_seconds": get_rotation_seconds(),
            "display_width": display_width,
            "display_height": display_height,
        },
    )


@app.get("/crop")
async def crop_queue_root():
    next_image = get_next_pending_image()
    if next_image is None:
        return RedirectResponse(url="/", status_code=303)
    return RedirectResponse(url=f"/crop/{next_image['id']}", status_code=303)


@app.get("/crop/{image_id}")
async def crop_image_page(request: Request, image_id: str):
    image = get_image(image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    if image.get("status") == "ready":
        return RedirectResponse(url="/", status_code=303)

    pending = get_pending_images()
    queue_ids = [img["id"] for img in pending]
    queue_position = queue_ids.index(image_id) + 1 if image_id in queue_ids else 1
    next_pending = get_next_pending_image(image_id)
    display_width, display_height = get_display_size()

    return templates.TemplateResponse(
        request,
        "crop.html",
        {
            "image": image,
            "queue_total": len(pending),
            "queue_position": queue_position,
            "next_pending_id": next_pending["id"] if next_pending else None,
            "display_width": display_width,
            "display_height": display_height,
        },
    )


@app.post("/crop/{image_id}/save")
async def save_cropped_image(
    image_id: str,
    processed_image: UploadFile = File(...),
    mode: str = Form("manual_cover"),
):
    image = get_image(image_id)
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found")

    payload = await processed_image.read()
    if not payload:
        raise HTTPException(status_code=400, detail="Processed image payload is empty")

    target_width, target_height = get_display_size()
    processed_path = save_processed_canvas_png(image_id, payload, target_width, target_height)
    ok = mark_image_ready(image_id, processed_path, mode)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update image state")

    next_pending = get_next_pending_image(image_id)
    next_url = f"/crop/{next_pending['id']}" if next_pending else "/"
    return {"status": "ok", "next_url": next_url}


@app.post("/upload")
async def upload_images(request: Request, files: list[UploadFile] | None = File(default=None)):
    uploads: list[UploadFile] = files or []

    # Fallback parser for clients that post under non-standard field names
    # such as "files[]" or "file".
    if not uploads:
        form = await request.form()
        for key in ("files", "files[]", "file"):
            value = form.getlist(key)
            uploads.extend([item for item in value if isinstance(item, UploadFile)])

    if not uploads:
        raise HTTPException(status_code=400, detail="No files were uploaded")

    accepted = 0
    for upload in uploads:
        if not upload.filename:
            continue
        if upload.content_type is None or not upload.content_type.startswith("image/"):
            continue
        image = await save_original_upload(upload)
        add_pending_image(image)
        accepted += 1

    if accepted == 0:
        raise HTTPException(status_code=400, detail="No valid image files found in upload")

    return RedirectResponse(url="/crop", status_code=303)


@app.post("/delete/{image_id}")
async def delete_image_route(image_id: str):
    deleted = delete_image(image_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Image not found")
    return RedirectResponse(url="/", status_code=303)


@app.post("/reorder")
async def reorder_route(request: Request):
    payload = await request.json()
    ids = payload.get("ids")
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        raise HTTPException(status_code=400, detail="Invalid reorder payload")

    ok = reorder_images(ids)
    if not ok:
        raise HTTPException(status_code=400, detail="IDs do not match current display images")

    return {"status": "ok"}


@app.get("/settings")
async def settings_page(request: Request):
    display_width, display_height = get_display_size()
    return templates.TemplateResponse(
        request,
        "settings.html",
        {
            "rotation_seconds": get_rotation_seconds(),
            "display_width": display_width,
            "display_height": display_height,
        },
    )


@app.post("/settings")
async def update_settings(
    rotation_seconds: int = Form(...),
    display_width: int = Form(...),
    display_height: int = Form(...),
):
    set_rotation_seconds(rotation_seconds)
    set_display_size(display_width, display_height)
    return RedirectResponse(url="/settings", status_code=303)

from __future__ import annotations

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .image_ops import ProcessMode, process_upload
from .scheduler import RotationScheduler
from .storage import (
    add_image,
    delete_image,
    get_images_sorted,
    get_rotation_seconds,
    reorder_images,
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
    return templates.TemplateResponse(
        request,
        "index.html",
        {"images": images, "rotation_seconds": get_rotation_seconds()},
    )


@app.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse(
        request,
        "settings.html",
        {"rotation_seconds": get_rotation_seconds()},
    )


@app.post("/upload")
async def upload_images(
    files: list[UploadFile] = File(...),
    mode: ProcessMode = Form("fit_crop"),
):
    for upload in files:
        if upload.content_type is None or not upload.content_type.startswith("image/"):
            continue
        image = process_upload(upload, mode)
        add_image(image)

    return RedirectResponse(url="/", status_code=303)


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
        raise HTTPException(status_code=400, detail="IDs do not match current images")

    return {"status": "ok"}


@app.post("/settings")
async def update_settings(rotation_seconds: int = Form(...)):
    set_rotation_seconds(rotation_seconds)
    return RedirectResponse(url="/settings", status_code=303)

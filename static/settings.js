(() => {
  const preset = document.getElementById("display_preset");
  const widthInput = document.getElementById("display_width");
  const heightInput = document.getElementById("display_height");

  if (!preset || !widthInput || !heightInput) return;

  const updatePresetFromInputs = () => {
    const key = `${widthInput.value}x${heightInput.value}`;
    const found = [...preset.options].find((opt) => opt.value === key);
    preset.value = found ? key : "custom";
  };

  preset.addEventListener("change", () => {
    if (preset.value === "custom") return;
    const [w, h] = preset.value.split("x");
    widthInput.value = w;
    heightInput.value = h;
  });

  widthInput.addEventListener("input", updatePresetFromInputs);
  heightInput.addEventListener("input", updatePresetFromInputs);
  updatePresetFromInputs();
})();

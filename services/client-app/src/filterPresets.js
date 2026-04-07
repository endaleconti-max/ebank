export function normalizePresetName(name) {
  return String(name || "").trim().replace(/\s+/g, " ");
}

export function upsertFilterPreset(existingPresets, preset) {
  const normalizedName = normalizePresetName(preset.name);
  if (!normalizedName) {
    throw new Error("Preset name is required");
  }

  const nextPreset = {
    name: normalizedName,
    filters: { ...preset.filters },
  };

  const remaining = existingPresets.filter(
    (candidate) => candidate.name.toLowerCase() !== normalizedName.toLowerCase(),
  );

  return [...remaining, nextPreset].sort((left, right) => left.name.localeCompare(right.name));
}

export function removeFilterPreset(existingPresets, presetName) {
  const normalizedName = normalizePresetName(presetName);
  return existingPresets.filter(
    (candidate) => candidate.name.toLowerCase() !== normalizedName.toLowerCase(),
  );
}

export function findFilterPreset(existingPresets, presetName) {
  const normalizedName = normalizePresetName(presetName);
  return existingPresets.find(
    (candidate) => candidate.name.toLowerCase() === normalizedName.toLowerCase(),
  ) || null;
}
AURA Desktop Icon — Photo-based (from your uploaded design)
================================================================
Background fully removed (AI-based segmentation), object tightly
cropped, centered on a transparent 1024x1024 square canvas.

aura_disc_object_only_transparent.png — the disc, native aspect ratio,
                                          full resolution, transparent bg
aura_master_1024.png                   — square-canvas version (used to
                                          generate everything below)

WINDOWS: aura_icon.ico -> frontend/build/icon.ico
LINUX:   aura_icon_16/24/32/48/64/128/256/512.png -> frontend/build/icons/
         (rename each to just its size, e.g. 16.png)
RUNTIME WINDOW ICON: aura_icon_256.png

Note: at very small sizes (16-32px) the fine copper emblem detail
inside the disc softens — expected for a photographic/painterly image
rather than a flat vector mark. The colorful swirl + circular shape
still reads clearly as a distinct icon at taskbar size.

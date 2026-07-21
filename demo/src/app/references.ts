const REFERENCE_IMAGES = [
  "knight_01_hero_34.png",
  "knight_02_front_ortho.png",
  "knight_03_side_ortho.png",
  "knight_04_back_ortho.png",
  "knight_05_bust_detail.png",
];

export function mountReferenceStrip(root: HTMLElement | null): void {
  if (!root) return;
  for (const name of REFERENCE_IMAGES) {
    const img = document.createElement("img");
    img.src = `/refs/${name}`;
    img.alt = name;
    img.title = name;
    root.appendChild(img);
  }
}

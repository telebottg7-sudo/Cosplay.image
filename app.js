const PAGE_SIZE = 24;
const manifestPath = "image/manifest.json";

const gallery = document.querySelector("#gallery");
const status = document.querySelector("#status");
const pagination = document.querySelector("#pagination");
const pageLabel = document.querySelector("#page-label");
const imageCount = document.querySelector("#image-count");
const pageCount = document.querySelector("#page-count");
const updatedAt = document.querySelector("#updated-at");

let images = [];
let currentPage = Number(new URLSearchParams(window.location.search).get("page")) || 1;

function setStatus(message, visible = true) {
  status.textContent = message;
  status.hidden = !visible;
}

function imageName(url) {
  const pathname = new URL(url).pathname;
  return decodeURIComponent(pathname.split("/").pop() || "Archive image").replace(/[_-]+/g, " ");
}

function renderGallery() {
  const totalPages = Math.max(1, Math.ceil(images.length / PAGE_SIZE));
  currentPage = Math.min(Math.max(currentPage, 1), totalPages);
  const start = (currentPage - 1) * PAGE_SIZE;
  const visibleImages = images.slice(start, start + PAGE_SIZE);

  imageCount.textContent = images.length.toLocaleString();
  pageCount.textContent = totalPages.toLocaleString();
  pageLabel.textContent = images.length ? `PAGE ${currentPage} / ${totalPages}` : "NO IMAGES";
  setStatus("", false);
  gallery.replaceChildren();

  visibleImages.forEach((url, index) => {
    const card = document.createElement("a");
    card.className = "image-card";
    card.href = url;
    card.target = "_blank";
    card.rel = "noreferrer noopener";
    card.style.setProperty("--delay", `${Math.min(index * 35, 350)}ms`);

    const image = document.createElement("img");
    image.src = url;
    image.alt = imageName(url);
    image.loading = "lazy";
    image.decoding = "async";
    image.addEventListener("error", () => card.classList.add("image-error"));

    const caption = document.createElement("span");
    caption.className = "image-caption";
    caption.textContent = imageName(url);

    const indexBadge = document.createElement("span");
    indexBadge.className = "image-index";
    indexBadge.textContent = String(start + index + 1).padStart(3, "0");

    card.append(image, indexBadge, caption);
    gallery.append(card);
  });

  renderPagination(totalPages);
  const nextUrl = new URL(window.location.href);
  nextUrl.searchParams.set("page", currentPage);
  window.history.replaceState({}, "", nextUrl);
}

function renderPagination(totalPages) {
  pagination.replaceChildren();
  if (totalPages <= 1) return;

  const addButton = (label, page, disabled = false, current = false) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = current ? "page-button current" : "page-button";
    button.textContent = label;
    button.disabled = disabled;
    if (current) button.setAttribute("aria-current", "page");
    button.addEventListener("click", () => {
      currentPage = page;
      renderGallery();
      document.querySelector(".gallery-section").scrollIntoView({ behavior: "smooth", block: "start" });
    });
    pagination.append(button);
  };

  addButton("←", currentPage - 1, currentPage === 1);
  const pages = new Set([1, totalPages, currentPage - 1, currentPage, currentPage + 1].filter((page) => page > 0 && page <= totalPages));
  let previous = 0;
  [...pages].sort((a, b) => a - b).forEach((page) => {
    if (page - previous > 1) {
      const gap = document.createElement("span");
      gap.className = "page-gap";
      gap.textContent = "…";
      pagination.append(gap);
    }
    addButton(String(page).padStart(2, "0"), page, false, page === currentPage);
    previous = page;
  });
  addButton("→", currentPage + 1, currentPage === totalPages);
}

async function loadImages() {
  try {
    const manifestResponse = await fetch(manifestPath, { cache: "no-store" });
    if (!manifestResponse.ok) throw new Error("The image manifest is not available yet.");
    const manifest = await manifestResponse.json();
    const chunks = Array.isArray(manifest.chunks) ? manifest.chunks : [];
    const responses = await Promise.all(chunks.map((chunk) => fetch(`image/${chunk}`, { cache: "no-store" })));
    if (responses.some((response) => !response.ok)) throw new Error("One or more image chunks could not be loaded.");
    const nestedImages = await Promise.all(responses.map((response) => response.json()));
    images = [...new Set(nestedImages.flat().filter((url) => typeof url === "string"))];
    updatedAt.textContent = "READY";
    renderGallery();
    if (!images.length) setStatus("The index is ready, but no image URLs have been added yet.");
  } catch (error) {
    updatedAt.textContent = "WAITING";
    pageLabel.textContent = "INDEX UNAVAILABLE";
    setStatus(error.message || "Unable to load the image index.");
  }
}

loadImages();

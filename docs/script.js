// Boutons « Copier » et lecteur de musiques. La page fonctionne sans ce script.

document.querySelectorAll("[data-copier]").forEach((bouton) => {
  const texte = bouton.getAttribute("data-copier");
  const etiquette = bouton.querySelector("span");
  const initial = etiquette.textContent;
  bouton.hidden = false;
  bouton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(texte);
      etiquette.textContent = "Copié !";
      bouton.dataset.etat = "ok";
    } catch {
      etiquette.textContent = "Sélectionnez la ligne et copiez-la";
    }
    setTimeout(() => {
      etiquette.textContent = initial;
      delete bouton.dataset.etat;
    }, 2400);
  });
});

let enCours = null;
document.querySelectorAll(".musique[data-son]").forEach((bouton) => {
  let audio = null;
  bouton.addEventListener("click", () => {
    if (!audio) {
      audio = new Audio(bouton.dataset.son);
      audio.preload = "auto";
      audio.addEventListener("waiting", () => (bouton.dataset.etat = "charge"));
      audio.addEventListener("playing", () => delete bouton.dataset.etat);
      audio.addEventListener("ended", () => bouton.setAttribute("aria-pressed", "false"));
      audio.addEventListener("error", () => {
        delete bouton.dataset.etat;
        bouton.setAttribute("aria-pressed", "false");
        bouton.querySelector("small").textContent = "Lecture impossible ici : téléchargez le fichier WAV depuis GitHub.";
      });
    }
    if (enCours && enCours !== audio) {
      enCours.pause();
      document.querySelectorAll('.musique[aria-pressed="true"]').forEach((b) => b.setAttribute("aria-pressed", "false"));
    }
    if (audio.paused) {
      bouton.dataset.etat = "charge";
      audio.play().catch(() => {});
      bouton.setAttribute("aria-pressed", "true");
      enCours = audio;
    } else {
      audio.pause();
      bouton.setAttribute("aria-pressed", "false");
    }
  });
});

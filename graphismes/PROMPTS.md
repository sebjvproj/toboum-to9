# Décors à générer avec un modèle d'image

Ce guide sert à fabriquer les **décors** de TOTO avec un modèle d'image. Donnez-lui **uniquement le texte** ci-dessous, jamais des images tirées d'un jeu existant : les monuments sont libres de droits, les dessins d'autrui ne le sont pas. Les 5 décors actuels (`sources/`) ont été faits ainsi.

## Comment faire

1. Générez chaque scène en **carré, 1024 × 1024 si possible**. Collez le bloc « Style commun » après la description de la scène.
2. Si le modèle le permet, ajoutez le **prompt négatif**.
3. Gardez les images qui ont **de grandes zones de couleur unie**. Évitez celles qui sont pleines de détails fins : ils disparaissent en 116 × 184 pixels.
4. Convertissez chaque image :
   ```sh
   cd outils
   python3 convertir_decor.py ../graphismes/sources/egypte.png --nom egypte --taille
   ```
   Ouvrez ensuite `graphismes/decors/egypte_apercu.png`. Le décor y est converti pour le TO9, avec quelques sprites posés dessus pour juger la lisibilité. L'image d'origine est affichée à droite.
5. Si le résultat ne convient pas, jouez sur ces réglages :
   - `--couleurs 5` ou `4` : moins de couleurs, donc plus lisible et plus petit en mémoire ;
   - `--tramage aucun` : des aplats sans tramage, plus compacts ;
   - `--tramage fs` : un rendu plus doux, mais plus lourd en mémoire ;
   - `--force 20` à `80` : l'intensité du tramage régulier.

Deux contraintes de lecture : le décor sert de fond derrière les bombes et les personnages, et ces sprites utilisent du noir, du blanc, des gris, du jaune, du rouge, du bleu et du vert vifs. Pour qu'ils ressortent, préférez des **décors aux tons moyens, un peu passés**, et **un centre d'image calme**.

**Vérifiez les conditions d'utilisation** de votre modèle d'image : le jeu est publié sous licence MIT, il faut donc avoir le droit de redistribuer les images produites.

## Style commun (à coller après chaque scène)

```
Retro 16-bit pixel art background for a single-screen arcade game.
Flat colors, large simple shapes, strong clear silhouette, limited palette of about 6 colors,
no gradients, no fine texture, no dithering noise.
Calm uniform sky in the upper third, simple flat ground in the bottom sixth,
the center of the image kept low-contrast and uncluttered because game objects will be drawn on top.
Muted, slightly desaturated mid-tone colors. Straight-on view, square image.
No text, no letters, no people, no characters, no animals, no user interface, no border, no frame.
Original artwork, do not imitate any existing video game.
```

## Prompt négatif

```
text, letters, watermark, signature, logo, people, person, character, animal, frame, border,
user interface, photorealistic, photo, 3d render, gradient, blur, noise, grain, lens flare, busy details
```

## Les 5 scènes

On part pour un tour du monde, avec un clin d'œil à la France et à TOetris.

### 1. Égypte : les pyramides au coucher du soleil
```
The three pyramids of Giza seen from far away at sunset, a few palm trees on the left,
warm orange and pink sky with one large pale sun, golden sand dunes in the foreground.
```

### 2. Rome : le Colisée l'après-midi
```
The Colosseum of Rome seen from the side in late afternoon light, a couple of umbrella pine trees,
clear pale blue sky with two small clouds, a flat stone-paved square in the foreground.
```

### 3. Moscou : Saint-Basile sous la neige
C'est le même monument que TOetris, pour faire le lien entre les deux jeux.
```
Saint Basil's Cathedral in Moscow at night under falling snow, colorful onion domes,
deep blue night sky with a few stars, snowy ground in the foreground.
```

### 4. Paris : la tour Eiffel la nuit
```
The Eiffel Tower at night seen from the banks of the Seine, a stone bridge in the distance,
dark violet night sky with a crescent moon, calm river reflecting a few lights in the foreground.
```

### 5. Mont-Saint-Michel à marée haute
```
Mont-Saint-Michel abbey on its rocky island at high tide on a bright day,
soft blue sky with a few flat clouds, calm sea surrounding the island, sandy shore in the foreground.
```

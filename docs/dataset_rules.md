# ProofOrigin Dataset Rules

## Goal
Build a clean, structured forensic dataset for training media authenticity AI models.

The dataset must prioritize:
- consistency
- traceability
- quality
- balanced labels
- reproducibility

---

# Label Categories

Each image should belong to ONE primary category only.

## Labels

### real
Authentic unmodified photographs captured by real cameras.

Examples:
- phone camera photos
- DSLR photos
- webcam captures

---

### ai_generated
Images created primarily using AI generation systems.

Examples:
- Midjourney
- ChatGPT image generation
- Stable Diffusion
- Flux
- Leonardo AI

---

### edited
Real images modified cosmetically without deceptive intent.

Examples:
- filters
- color grading
- brightness edits
- resized images

---

### manipulated
Images intentionally altered to deceive or fabricate reality.

Examples:
- face swaps
- object insertion
- fake scenes
- altered evidence
- deceptive composites

---

### screenshot
Screen captures from devices or platforms.

Examples:
- TikTok screenshots
- X posts
- Discord screenshots
- YouTube screenshots
- Telegram captures

---

# Dataset Rules

## 1. Preserve Originals
Never overwrite original files.

Raw files must remain inside:

data/raw/

Processed files belong in:

data/processed/

---

## 2. Minimum Quality
Avoid:
- blurry thumbnails
- tiny compressed images
- corrupted files

Preferred minimum:
512x512 resolution

---

## 3. Source Diversity
Collect from multiple platforms and devices.

Avoid overfitting to:
- one AI model
- one camera
- one social platform

---

## 4. File Naming Convention

Use descriptive filenames.

Good:
iphone_real_001.jpg
midjourney_ai_001.png
discord_screen_001.jpg

Bad:
image1.jpg
testlol.png
random.jpg

---

## 5. Metadata Tracking

Each important image should eventually track:

- filename
- label
- source
- detector_score
- human_feedback
- final_label

Future metadata:
- ai_model
- camera_model
- resolution
- compression
- platform
- edit_software

---

## 6. Balanced Dataset

Avoid heavily imbalanced categories.

Target early balance:

100 real
100 ai_generated
100 edited
100 manipulated
100 screenshot

---

## 7. Human Verification

Labels should eventually be reviewed by humans.

Human-reviewed datasets are more valuable than scraped datasets.

---

## 8. Safety Rules

Do NOT collect:
- illegal content
- private leaks
- harmful exploit material
- copyrighted datasets without permission

---

# Long-Term Vision

ProofOrigin aims to build:
- forensic preprocessing systems
- authenticity scoring pipelines
- media provenance intelligence
- hybrid AI + human verification systems

The dataset is the foundation of the entire ecosystem.

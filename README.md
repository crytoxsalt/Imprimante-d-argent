# Imprimante d'argent

Generate narrated vertical videos from Reddit-style stories.

## Structure

- `main.py` - root launcher; keeps `python main.py` working.
- `src/imprimante_argent/` - application package.
- `assets/` - reusable media assets such as the base video, title card, and fonts.
- `output/` - generated videos and preview images.
- `temp/` - temporary audio, captions, and card files created during a run.

## Usage

```powershell
pip install -r requirements.txt
python main.py
```

Optionally pass a subreddit name:

```powershell
python main.py AmItheAsshole
```

# Pushing this to GitHub

The repository already has two commits. Nothing needs to be rebuilt.

1. Create an empty repository on GitHub. No README, no .gitignore, no licence,
   since this repository already has all three. Suggested name:

       aioe-isco08-crosswalk

2. From inside this folder:

```
git remote add origin https://github.com/YOUR_USERNAME/aioe-isco08-crosswalk.git
git branch -M main
git push -u origin main
```

3. In the repository settings, set the description to:

       AIOE occupational AI-exposure scores carried from 2010 SOC onto ISCO-08,
       with the transfer error reported rather than averaged away.

That is all. The outputs in `out/` are committed, so the crosswalk is usable
from the repository page without anyone running the pipeline.

# Pushing this to GitHub

The repository is already created at

    https://github.com/Lombergine/aioe-isco08-crosswalk

and the remote is already configured in this folder. You do not need to set
anything up.

From inside this folder, run:

```
git pull --rebase origin main
git push -u origin main
```

The first command picks up the single `.gitattributes` commit that already
exists on GitHub. The second pushes everything else.

If git asks for a password, use a personal access token rather than your
account password. GitHub stopped accepting passwords for this in 2021.

## If you would rather not use the terminal

1. Unpack this archive.
2. Go to https://github.com/Lombergine/aioe-isco08-crosswalk/upload/main
3. Drag the `crosswalk` folder's contents onto that page. GitHub keeps the
   subfolder structure when you drag a folder.
4. Commit.

This route loses the commit history but puts every file in the right place.

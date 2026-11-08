# Contributing

Thanks for wanting to help! Second Brain Studio is a spare-time project, so a few simple rules keep it manageable.

- **Bugs**: open an [issue](../../issues/new/choose) with the app version and, if you can, the lines from `app-errori.log`. Check them for anything personal first.
- **Ideas and questions**: start a thread in [Discussions](../../discussions). Issues are for things that are clearly broken or clearly agreed on.
- **Pull requests**: small fixes (typos, translations, obvious bugs) are welcome straight away. For anything bigger, open an issue first so we can agree on the approach before you spend time on it.

## Working on the code

```powershell
py -3.14 -m pip install --user -r app\requirements.txt
python -m pytest -q                 # all tests must pass
python app\main.py --debug          # run from source
```

The interface can be worked on in a normal browser, with made-up data and no Python:
`python -m http.server 8765 -d app\web`, then open `http://127.0.0.1:8765/prova.html`
(parameters are listed at the top of `prova.html`; `?en` switches to English).

- The code and comments are in Italian; English is welcome in issues and pull requests.
- The interface is written in Italian and translated live: new texts need an entry in `app/web/lingua-en.mjs`.
- Never put real personal data in tests, screenshots or `prova.html`: use made-up people and projects.
- README screenshots are made with `docs\immagini\screenshot.ps1`.

## License of contributions

By sending a pull request you agree that your contribution is released under the project's
[PolyForm Noncommercial 1.0.0](LICENSE.md) license.

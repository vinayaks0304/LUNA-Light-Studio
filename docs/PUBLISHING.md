# Publishing LUNA on GitHub

The repository is designed to be uploaded **as source**, with builds and releases created separately. These commands are intended to run on your Linux machine in the root of the extracted repository.

## Before publishing

1. Review the repository for private information and personal device identifiers.
2. Choose a licence using [LICENSING.md](LICENSING.md). Until you add one, others have no general permission to reuse the code.
3. Add **your own** screenshots of the Linux, Windows and Android apps. Do not use screenshots of private settings, addresses or unrelated accounts.
4. Run the desktop tests and build Android locally.
5. Make sure the source does not contain APK decompilations, proprietary binaries, raw Bluetooth captures, keystores, tokens or local SDK paths.

## Option A — GitHub CLI (recommended)

Install Git and GitHub CLI on CachyOS:

```bash
sudo pacman -S --needed git github-cli
```

In the repository root:

```bash
gh auth login
git init
git branch -M main
git add .
git commit -m "Initial release: LUNA for Linux, Windows and Android"
gh repo create LUNA-Light-Studio --public --source=. --remote=origin --push
```

`gh auth login` is interactive. The `gh repo create` command creates a repository under the GitHub account you authenticate with; change `LUNA-Light-Studio` if you want another name. If the repository already exists, **do not run `gh repo create` again**; add its remote URL and push instead.

## Option B — GitHub website

Create a new empty public repository at <https://github.com/new> named `LUNA-Light-Studio` (do **not** initialise it with a README if you're pushing this project). Then:

```bash
git init
git branch -M main
git add .
git commit -m "Initial release: LUNA for Linux, Windows and Android"
git remote add origin https://github.com/YOUR_USERNAME/LUNA-Light-Studio.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username. GitHub requires authentication for pushing; use `gh auth login`, a credential manager or SSH rather than placing a personal access token directly in a command or file.

## Recommended repository settings

- **Description:** `Cross-platform Bluetooth LED controller for Linux, Windows and Android, built with PySide6, Bleak and Kotlin.`
- **Topics:** `bluetooth-low-energy`, `python`, `pyside6`, `kotlin`, `android`, `linux`, `windows`, `reverse-engineering`, `led-controller`.
- **About website:** Leave blank until you have a real project site.
- **README:** Already included.
- **Issues:** Enable for bug reports and hardware compatibility feedback.
- **Discussions:** Optional for feature requests and controller research.

## Releases

For a first source-only release, tag a version after the code and docs are reviewed:

```bash
git tag v0.5.1
git push origin v0.5.1
```

The desktop and Android versions have historically used different numbering, so this tag should be described as a **repository snapshot**, not a claim that all platforms share the same release version.

When ready, attach **locally built and tested** Linux and Windows bundles and a signed Android APK to a GitHub Release. Don't upload a debug keystore, sign-in credentials, or a release APK you haven't tested. The repository currently contains source and build scripts, not verified prebuilt distribution packages.

## Suggested screenshots

A good README gallery would show: (1) Linux dashboard with adaptive theme, (2) Colour Studio and saved colours, (3) Windows desktop UI, and (4) Android colour wheel. Add images under `docs/images/` and link them from the README only after capturing them from the real applications.

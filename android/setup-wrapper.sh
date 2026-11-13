#!/usr/bin/env bash
# Bootstrap an official Gradle wrapper using a locally installed Gradle.
# We cannot bundle the official wrapper JAR without fetching it from Gradle.
set -Eeuo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v gradle >/dev/null 2>&1; then
  echo 'Install Gradle first (CachyOS: sudo pacman -S --needed gradle).' >&2
  exit 1
fi
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT
printf 'tasks.register("hello")\n' > "$TMP/build.gradle.kts"
(cd "$TMP" && gradle wrapper --gradle-version 8.7 --distribution-type bin --no-validate-url)
cp "$TMP/gradlew" "$TMP/gradlew.bat" "$ROOT/"
cp "$TMP/gradle/wrapper/gradle-wrapper.jar" "$ROOT/gradle/wrapper/"
chmod +x "$ROOT/gradlew"
echo 'Official Gradle wrapper generated. Run ./gradlew assembleDebug (Android SDK required).'

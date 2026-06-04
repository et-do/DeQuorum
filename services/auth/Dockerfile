# Firebase emulator suite for local-only auth testing.
#
# The image installs the Firebase CLI + Java (required by the auth emulator)
# and starts only the auth + emulator-UI services. In production we use the
# real Firebase Auth — the DeQuorum app talks to either through the same
# REST endpoints, so swapping is configuration only.

FROM node:26-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
 && apt-get install -y --no-install-recommends openjdk-17-jre-headless \
 && rm -rf /var/lib/apt/lists/* \
 && npm install -g firebase-tools

WORKDIR /firebase
COPY firebase.json ./
COPY .firebaserc ./

# 9099 = Auth emulator REST; 4000 = emulator UI.
EXPOSE 9099 4000

CMD ["firebase", "emulators:start", "--only", "auth"]

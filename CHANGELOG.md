# Changelog

## [1.3.0](https://github.com/chris2k20/imapbackup/compare/v1.2.0...v1.3.0) (2025-10-10)


### Features

* disable automatic key retrieval during GPG encryption ([ad827c6](https://github.com/chris2k20/imapbackup/commit/ad827c6448f22d343186b728338127289c602f0c))

## [1.2.0](https://github.com/chris2k20/imapbackup/compare/v1.1.1...v1.2.0) (2025-10-10)


### Features

* prevent S3 upload if GPG encryption fails for any files ([9292d95](https://github.com/chris2k20/imapbackup/commit/9292d95ecdb96292d1bc22704e793ee3b63a5c41))

## [1.1.1](https://github.com/chris2k20/imapbackup/compare/v1.1.0...v1.1.1) (2025-10-10)


### Bug Fixes

* abort backup when GPG key import fails to prevent unencrypted data exposure ([87bf75b](https://github.com/chris2k20/imapbackup/commit/87bf75b944a56b6d730a5ab649dd41074232d9ef))
* **Dockerfile:** add curl package to Docker image dependencies ([49b6343](https://github.com/chris2k20/imapbackup/commit/49b6343fa20d4545050028f472632e0f08c034ea))

## [1.1.0](https://github.com/chris2k20/imapbackup/compare/v1.0.0...v1.1.0) (2025-10-10)


### Features

* add network retry logic for IMAP operations and S3 transfers ([380641f](https://github.com/chris2k20/imapbackup/commit/380641f771f27291ebd3dcf7417f741b8c958a87))
* add progress tracking and memory optimization for large mailbox processing ([1254123](https://github.com/chris2k20/imapbackup/commit/1254123d410dfc81db8addd564703f14584e630c))


### Bug Fixes

* **Dockerfile:** run script via python3 to avoid shebang env -S compatibility issues ([ff506d2](https://github.com/chris2k20/imapbackup/commit/ff506d248ada0b2cbf1d3e566f4d92f050e07362))

## 1.0.0 (2025-10-10)


### Features

* add auto-detection of config.yaml when running without arguments ([38cfbb4](https://github.com/chris2k20/imapbackup/commit/38cfbb4204e3b26fe3af24dfe56c5ece1a0575c3))
* add backup listing, selective account filtering, and date-based restore capabilities ([030d8b4](https://github.com/chris2k20/imapbackup/commit/030d8b4622d6df61bc49365b4b8b51af647acb94))
* add date-based folder organization with configurable date formats ([98fb7f1](https://github.com/chris2k20/imapbackup/commit/98fb7f16f054e502de5f641dfb1009e38e6822f1))
* add GitHub Pages deployment with Jekyll and SEO optimization ([734d477](https://github.com/chris2k20/imapbackup/commit/734d477f0dd30aa31462c86e21f4d2c0ac24eff5))
* add multi-account backup support with YAML configuration and GitHub Pages setup ([9593c81](https://github.com/chris2k20/imapbackup/commit/9593c815fed0cb91d9f664bee8560fd4e0dd1cd4))
* **Docker:** add Docker support with multi-arch builds and automated publishing workflow ([6c67b4d](https://github.com/chris2k20/imapbackup/commit/6c67b4d3808bd832aa027373b35ae2beda13c2b3))
* **restore:** add restore mode to upload messages from mbox files to IMAP server ([c0aa276](https://github.com/chris2k20/imapbackup/commit/c0aa276467f34ff550a5ea8e2f121f8d24324f8a))
* **s3-gpg-restore:** add S3 download and GPG decryption support for IMAP restore operations ([5293031](https://github.com/chris2k20/imapbackup/commit/5293031b728deeaefe58e46a970595afb8920910))
* **s3-gpg:** add GPG encryption and S3 upload support for IMAP backups ([8ffb19e](https://github.com/chris2k20/imapbackup/commit/8ffb19edbd6fd512ee476d0c9b1fd5e699597880))


### Bug Fixes

* 19 ([fb85944](https://github.com/chris2k20/imapbackup/commit/fb8594432f46defca49411215d7f0f0228fb4b03))
* 2 ([82e6071](https://github.com/chris2k20/imapbackup/commit/82e6071fb3733ff1540dc8595b4596fc16141ec3))

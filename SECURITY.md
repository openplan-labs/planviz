# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |

## Reporting a vulnerability

planviz renders figures with matplotlib. It opens no network connections, and
the only files it writes are the ones you pass to `save` or `save_animation`.
Its attack surface is therefore small but not empty: it reads a bundled
stylesheet, it shells out to `ffmpeg` when asked to write an MP4, and it will
happily write to any path a caller hands it.

If you believe you have found a security issue — for example a path handled
unsafely, or an input that makes the library read or execute something it
should not — please report it privately:

- Email **erwin.lejeune15@gmail.com** with a description, a minimal
  reproduction, and the affected version.
- Or use GitHub's private vulnerability reporting on this repository
  (Security → Report a vulnerability).

You will get an acknowledgement within a week. Please do not open a public
issue for a suspected vulnerability before a fix is released.

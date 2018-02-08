# Waterslide's changelog
Reverse chronological changelog, with formatting loosely based upon
[Keep a Changelog](http://keepachangelog.com/en/1.0.0/), with dates
standarised to iso-8601.

## Versioning
The project versioning is loosely based upon a combination of git-describe and
git-tag; the general idea of [semver](http://semver.org/spec/v2.0.0.html);
and [pep440](https://www.python.org/dev/peps/pep-0440/) for package versioning.

The format obtained by invoking `waterslide version --release` is in the format
of `v<semver>[-<distance>-<build commit>]`, where the part between square
brackets will only appear when the distance (as determined by git-describe) to
the last versioning tag is greater than 0 (i.e.: not build from that commit)

The format of the package version is based upon the data from the above
command, in the format of `<semver>[.dev<distance>]`. The above rules apply
here too.

# [UNRELEASED]

# [0.2.1] 2018-2-8
## Added
- Docker support

## Changed
- Import presentations as utf-8

# [0.2.0] 2017-9-4
## Added
- Password protection of presentation master control with BasicAuth and a
  presentation config file (conf.yaml)
- cmdline flag to enable tracing of multiplexing messages (which heretofore
  always happened, now disabled by default.)
- Multiplexing sessions, to be able to run multiple presentations in
  parallel without the controls clashing
- sha512 and md5 as socket-id hashing algorithms
- cmdline flags to enable/disable autoslaving of presentation requests which
  aren't masters
- Manager subcommand, to automatically manage (and cache) presentations in
  a document root. Presentations within this document root can be
  added/changed/removed at will.
- Configuration dump subcommand, to get paths to resources which can then be
  served by another webserver
- Disabling static routes now possible, for when a _real_ webserver handles it

## Changed
- Default hashing algorithm is now md5 insteadof bcrypt

## Fixed
- Head.js is now included when multiplexing is the only plugin
- send_direct() reads files as binary insteadof text

## Removed
- WaterSlide no longer searches by itself for a local reveal.js repository
- Bcrypt as a socket-id hashing algorithm

# [0.1.0] 2017-8-27
Bumped version number to get in line with semver.

## Added
- No caching of the HTML when multiplexing
- Semi-automatic versioning using git-tag and git-describe
- Python wheel (.whl) packaging support

## Changed
- Default listening address from 127.0.0.1 to 0.0.0.0 for least astonishment
  ("Why doesn't multiplexing on my phone work?")
- Brought the README up to date

# [0.0.1] 2017-8-25
## Added
- Doxygen based documentation
- CLI flag to disable caching
- Multiplex feedback loop prevention
- Semi-automatic presentation multiplexing
- Static file serving

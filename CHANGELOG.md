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

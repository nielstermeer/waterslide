# WATERSLIDE: Reveal.js based presentation software
WaterSlide is a python 3 based program which abstracts away all the nasty
parts (writing links, initialisation code, etc) of Reveal.js presentations.

The program, and the "file format" it uses is supposed to play nice with
version control systems. It does this by only storing the core of the
presentation with it's configuration in the index file, along with any images,
stylesheets or scripts made for that presentation. It does not require that
Reveal.js is available on the local machine.

# Quick Feature TL;DR
- simple, quick presentation creation without having to search for the proper
  links, or having to download the whole library, plus required dependencies.
- friendly to VCS's
- fool-proof .scss handling
- automatic presentation multiplexing
- Good for local presentations, or behind a "proper" webserver

# Basic Setup
This setup assumes that WaterSlide is already installed on your system. Refer
to the "example-presentations" directory for some example presentations.

1. Create a directory in which the presentation will be created
2. Write a presentation by putting the presentation's core
   (so anything inside the "`<div class="reveal"><div class="slides">`"
   structure) in the "index.html" file. For syntax, refer to
   [Reveal.js's](https://github.com/hakimel/reveal.js) manual, and to
   the [syntax addendum](#Syntax)
3. Put all the files you want to use, such as images, in said directory.
4. Run `waterslide serve .` in said directory. WaterSlide will now serve the
   html, stylesheets, and static resources.
5. Navigate to "localhost:9090" in your browser, to start presenting.

# Syntax
The index.html file contains two sections one optional section (the yaml
formatted configuration, documented in doc/conf-doc.yaml) and one required part
(the presentation's core. It is currently only in html, but markdown support is
in the pipeline). The configuration and content are separated by the string
"\n<!-- EOC -->\n"

# URL/Path structure
The url structure depends on the way the program was invoked. The serve
subcommand will drop all the presentations in the root directory, without using
nested directories. The manage subcommand, on the contrary, will map the request
to directories in the document root.

# Program Invocation
WaterSlide uses a `<cmdname> [opts] [<subcmdname> [subcmdopts] [--] [files]]`
commandline structure. All the commands and subcommands support the '-h' and
'--help' command line flags. Use these to get their helptext's

## Deployment methods
The WaterSlide program currently uses two subcommands to present presentations,
which are "serve" and "manage". The way they achieve their goal is different
though.

The "serve" subcommand requires the user to name all the presentations which are
to be served. It does not check for new presentations at runtime, although it
does refresh the presentation's source code if it is changed while the program
is running. This subcommand is useful for local presentations.

Contrast this with the "manage" subcommand. The only thing it requires is it's
document root. It does not load all the presentations on startup, but rather it
waits on a request for a presentation, and then loads (and caches) it. The cache
then checks on each request whether or not the requested presentation has
changed and still exists. This subcommand is useful for server deployments.

## Server configuration file
Each presentation can have it's own server configuration file. It must be named
'conf.yaml' and be formatted in yaml. It must also be in the root directory of the
presentation. Keep in mind that this file is in the document root, and must be
protected by your server accordingly.

Since the configuration is somewhat tree-shaped, this readme will refer to this
configuration file and the contained configuration parameters using a dot
separated path. It also uses a comma separated list within '{}' to denote a list
of configuration parameters at that path.

## Invocation examples
This is a non-exhaustive list of invocation examples, which might be useful to
get started. Check each subcommand's helptext for more information, or for the
longer version of a commandline flag.

~~~~~~{.bash}
# Serve the current working directory as a presentation, using the built-in
# default configuratio configuration
waterslide serve .

# As above, but enable multiplexing
waterslide serve -m .

# Manage a document root of presentations, and enable the multiplexing server
waterslide manage -M .

# Change the multiplex endpoint url. This is useful for when we run behind a
# proper webserver
waterslide manage -M -X https://slides.example.com .
~~~~~~


# SASS/SCSS stylesheets
WaterSlide will automatically transpile sass and scss stylesheets to css upon
request, with no user interaction required. Use the filename of the file on
disk, not the filename with .css as extenstion (i.e. foo.scss, not foo.css).
WaterSlide will automatically send the appropriate headers and link attributes
to get the browser to recognise it as a stylesheet.


# Multiplexing
WaterSlide features a largely fool-proof and automatic presentation multiplexing
system. It does not require any user configuration, besides credential
configuration when required, and the use of the correct url.

The multiplexing subsystem is tolerant of multiple masters on the network, which
can be used to, for example, to hook up a laptop to a beamer (to still have a
keyboard to control the presentation), and then control the presentation
alongside the laptop with your smartphone.

## URL structure
The presentation's multiplexing state is controlled through url query
parameters. '?master' will cause the presentation to obtain master control
(assuming that the credentials are correct, when the presentation is behind a
password). '?slave' will cause it to be slaved to a master.

Queries in the form of '?master=foo' or '?slave=foo' will cause the presentation
to obtain control of, or be slaved to, the session named 'foo'. Using this, one
can run multiple multiplex "sessions" with them not interfering with eachother.

## Autoslaving
When using the serve subcommand, all presentations which do not explicitly
request master control of the presentation will be automatically be slaved to
the "global" session (i.e.: '?master', not '?master=foo'). A presentation can
request to be slaved to another session by explicitly passing a session with the
query parameters (e.g. '?slave=foo').

The manage subcommand does not autoslave clients, they have to explicitly
request to be slaved. This is so that people can leisurely study a
presentation, without being dragged along when that presentation is also being
used as a multiplexed presentation.

## Password protection
Each presentation can be protected by a username:password combination with
http-basicauth, with the credentials stored in plain-text[^ptcredentials] in the
configuration file. (under multiplex.auth.{uname, passwd})


# Licence
This program is licensed under the Mozilla Public License, version 2.0.



[^ptcredentials]: Yes I know, generally storing passwords in plain text is a
very-bad-idea(tm). But these credentials are not to be used to store highly
sensitive information, but to thwart attacks from aspiring dictators which see
the '?master' query. I thought it was important to have an easily configurable
configuration file than to have _super_ _secure_ credential system. For those
whising for hashed passwords, fear not, I'm mulling over how to do this nicely
without interfering with "the simple way"(tm).

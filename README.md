# WATERSLIDE: Reveal.js based presentation software
Waterslide is a python based program which abstracts away all the nasty
parts of reveal.js presentations, and separates management html from
the actual presentation. It is also supposed to play very nice with source
control systems.

# How to use: TL;DR
Put a bunch of files you need in a directory, along with the core of the
presentation (so anything inside the "`<div class="reveal"><div class="slides">`"
structure) in the file 'index.html', point waterslide at it with
`waterslide serve <dirname>`, goto localhost:9090 in your browser,
and you're good to go.

# How to use: The longer version

## The presentation itself
Consider the directory named "example" (see ./examples/example in the project
root). The presentation itself, along with the configuration is located
in the file index.html, like this:

~~~~~~
title: Waterslide presentation Configuration
theme: black
styles:
 - 'foo.scss'
scripts:
 - 'baz.js'
<!-- EOC --> <!-- <-- that there, is the separation between config and content-->
<section>
<h1>Hello World!</h1>
</section>
<section>
<h1>This an example Waterslide/Reveal.js presentation</h1>
</section>
~~~~~~

Anything above the string `<!-- EOC -->` (watch the spaces) is considered
configuration for the presentation, in YAML. Anything below the actual
reveal.js presentation core.

## Custom stylesheets
Custom stylesheets are put directly next to index.html in the presentation
directory. Then they are listed in the "styles" configuration directive in a
list. The name listed should directly correspond to the name used on disk.
SCSS stylesheets are fully supported through libsass-python, and are compiled
on demand, no further action required

## Custom javascript
Custom javascript files are just as easily used as the stylesheets. List them
in the "scripts" configuration directive in a list.

## Miscellaneous configuration directive
- title: Specify the title of the presentation. If not provided, Waterslide
	will use the name of the directory it is located in.
- theme: Reveal.js theme Waterslide will link to. If not specified, it defaults
	to black (soo nice on the eyes:).

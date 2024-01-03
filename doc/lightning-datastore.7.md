lightning-datastore -- Command for storing (plugin) data
========================================================

SYNOPSIS
--------

**datastore** *key* [*string*] [*hex*] [*mode*] [*generation*]

DESCRIPTION
-----------

The **datastore** RPC command allows plugins to store data in the
Core Lightning database, for later retrieval.

RETURN VALUE
------------

[comment]: # (GENERATE-FROM-SCHEMA-START)
On success, an object is returned, containing:

- **key** (array of strings):
  - Part of the key added to the datastore
- **generation** (u64, optional): The number of times this has been updated
- **hex** (hex, optional): The hex data which has been added to the datastore
- **string** (string, optional): The data as a string, if it's valid utf-8

[comment]: # (GENERATE-FROM-SCHEMA-END)

ERRORS
------

The following error codes may occur:

- 1202: The key already exists (and mode said it must not)
- 1203: The key does not exist (and mode said it must)
- 1204: The generation was wrong (and generation was specified)
- 1205: The key has children already.
- 1206: One of the parents already exists with a value.
- -32602: invalid parameters

AUTHOR
------

Rusty Russell <<rusty@rustcorp.com.au>> is mainly responsible.

SEE ALSO
--------

lightning-listdatastore(7), lightning-deldatastore(7), lightning-datastoreusage(7)

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[comment]: # ( SHA256STAMP:36976b15cda1e013713b88f2411da5900b169d99c87ee30b5e8389e45a0df68a)

lightning-autoclean-status -- Examine auto-delete of old invoices/payments/forwards
===================================================================================

SYNOPSIS
--------

**autoclean-status** [*subsystem*]

DESCRIPTION
-----------

The **autoclean-status** RPC command tells you about the status of
the autclean plugin, optionally for only one subsystem.

RETURN VALUE
------------

Note that the ages parameters are set by various `autoclean-...-age`
parameters in your configuration: see lightningd-config(5).

On success, an object containing **autoclean** is returned. It is an object containing:

- **succeededforwards** (object, optional)
  - **enabled** (boolean): whether autocleaning is enabled for successful listforwards
  - **cleaned** (u64): total number of deletions done (ever)

  If **enabled** is *true*:
    - **age** (u64): age (in seconds) to delete successful listforwards

- **failedforwards** (object, optional)
  - **enabled** (boolean): whether autocleaning is enabled for failed listforwards
  - **cleaned** (u64): total number of deletions done (ever)

  If **enabled** is *true*:
    - **age** (u64): age (in seconds) to delete failed listforwards

- **succeededpays** (object, optional)
  - **enabled** (boolean): whether autocleaning is enabled for successful listpays/listsendpays
  - **cleaned** (u64): total number of deletions done (ever)

  If **enabled** is *true*:
    - **age** (u64): age (in seconds) to delete successful listpays/listsendpays

- **failedpays** (object, optional)
  - **enabled** (boolean): whether autocleaning is enabled for failed listpays/listsendpays
  - **cleaned** (u64): total number of deletions done (ever)

  If **enabled** is *true*:
    - **age** (u64): age (in seconds) to delete failed listpays/listsendpays

- **paidinvoices** (object, optional)
  - **enabled** (boolean): whether autocleaning is enabled for paid listinvoices
  - **cleaned** (u64): total number of deletions done (ever)

  If **enabled** is *true*:
    - **age** (u64): age (in seconds) to paid listinvoices

- **expiredinvoices** (object, optional)
  - **enabled** (boolean): whether autocleaning is enabled for expired (unpaid) listinvoices
  - **cleaned** (u64): total number of deletions done (ever)

  If **enabled** is *true*:
    - **age** (u64): age (in seconds) to expired listinvoices


AUTHOR
------

Rusty Russell <<rusty@rustcorp.com.au>> is mainly responsible.

SEE ALSO
--------

lightningd-config(5), lightning-listinvoices(7),lightning-listpays(7), lightning-listforwards(7)

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[comment]: # ( SHA256STAMP:dbb5c220be93580a35a686e5a32d58fa0c452185f32a9ea7c298de8bfd1cb12b)

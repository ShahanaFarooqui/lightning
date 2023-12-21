lightning-withdraw -- Command for withdrawing funds from the internal wallet
============================================================================

SYNOPSIS
--------

**withdraw** *destination* *satoshi* [*feerate*] [*minconf*] [*utxos*]

DESCRIPTION
-----------

The **withdraw** RPC command sends funds from Core Lightning's internal
wallet to the address specified in *destination*.

RETURN VALUE
------------

[comment]: # (GENERATE-FROM-SCHEMA-START)
On success, an object is returned, containing:

- **tx** (hex): the fully signed bitcoin transaction
- **txid** (txid): the transaction id of *tx*
- **psbt** (string): the PSBT representing the unsigned transaction

[comment]: # (GENERATE-FROM-SCHEMA-END)

ERRORS
------

On failure, an error is reported and the withdrawal transaction is not
created.

The following error codes may occur:

- -1: Catchall nonspecific error.
- 301: There are not enough funds in the internal wallet (including
fees) to create the transaction.
- 302: The dust limit is not met.
- 313: The `min-emergency-msat` reserve not be preserved (and we have anchor channels).

AUTHOR
------

Felix <<fixone@gmail.com>> is mainly responsible.

SEE ALSO
--------

lightning-listfunds(7), lightning-fundchannel(7), lightning-newaddr(7),
lightning-txprepare(7), lightning-feerates(7).

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[comment]: # ( SHA256STAMP:38527c3337263c9b4681c976a8148acaaa544f94beb576f2a91b584c3488bfc3)

lightning-fundchannel\_start -- Command for initiating channel establishment for a lightning channel
====================================================================================================

SYNOPSIS
--------

**fundchannel\_start** *id* *amount* [*feerate* *announce* *close\_to* *push\_msat*]

DESCRIPTION
-----------

`fundchannel_start` is a lower level RPC command. It allows a user to
initiate channel establishment with a connected peer.

Note that the funding transaction MUST NOT be broadcast until after
channel establishment has been successfully completed by running
`fundchannel_complete`, as the commitment transactions for this channel
are not secured until the complete command succeeds. Broadcasting
transaction before that can lead to unrecoverable loss of funds.

RETURN VALUE
------------

[comment]: # (GENERATE-FROM-SCHEMA-START)
On success, an object is returned, containing:

- **funding\_address** (string): The address to send funding to for the channel. DO NOT SEND COINS TO THIS ADDRESS YET.
- **scriptpubkey** (hex): The raw scriptPubkey for the address
- **close\_to** (hex, optional): The raw scriptPubkey which mutual close will go to; only present if *close\_to* parameter was specified and peer supports `option_upfront_shutdown_script`
- **mindepth** (u32, optional): Number of confirmations before we consider the channel active.

The following warnings may also be returned:

- **warning\_usage**: A warning not to prematurely broadcast the funding transaction (always present!)

[comment]: # (GENERATE-FROM-SCHEMA-END)

ERRORS
------

On error the returned object will contain `code` and `message` properties,
with `code` being one of the following:

- -32602: If the given parameters are wrong.
- -1: Catchall nonspecific error.
- 300: The amount exceeded the maximum configured funding amount.
- 301: The provided `push_msat` is greater than the provided `amount`.
- 304: Still syncing with bitcoin network
- 305: Peer is not connected.
- 306: Unknown peer id.

AUTHOR
------

Lisa Neigut <<niftynei@gmail.com>> is mainly responsible.

SEE ALSO
--------

lightning-connect(7), lightning-fundchannel(7), lightning-multifundchannel(7),
lightning-fundchannel\_complete(7), lightning-fundchannel\_cancel(7)
lightning-openchannel\_init(7), lightning-openchannel\_update(7),
lightning-openchannel\_signed(7), lightning-openchannel\_bump(7),
lightning-openchannel\_abort(7)

RESOURCES
---------

Main web site: <https://github.com/ElementsProject/lightning>

[comment]: # ( SHA256STAMP:ed685f91a9242a38a2d48b82ed7ba063a1a4d754d95283ad232cbe7d12471659)

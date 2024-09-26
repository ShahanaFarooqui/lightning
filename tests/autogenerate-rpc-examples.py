# This script is used to re-generate all RPC examples for methods listed in doc/schemas/lightning-*.json schema files.
# It uses the pre existing test setup to start nodes, fund channels and execute other RPC calls to generate these examples.
# This test will only run with GENERATE_EXAMPLES=True setup to avoid accidental overwriting of examples with other test executions.
# Set the test TIMEOUT to more than 3 seconds to avoid failures while waiting for the bitcoind response. The `dev-bitcoind-poll` is set to 3 seconds, so a shorter timeout may lead to test failures.
# Note: Different nodes are used to record examples depending upon the availability, quality and volume of the data. For example: Node l1 has been used to listsendpays and l2 for listforwards.

from fixtures import *  # noqa: F401,F403
from fixtures import TEST_NETWORK
from io import BytesIO
from pathlib import PosixPath
from pyln.client import RpcError, Millisatoshi
from pyln.proto.onion import TlvPayload
from utils import only_one, mine_funding_to_announce, sync_blockheight, wait_for, first_scid, GenChannel, generate_gossip_store
import os
import re
import time
import pytest
import unittest
import json
import logging
import ast
import struct
import subprocess
import socket
import shutil

CWD = os.getcwd()
REGENERATING_RPCS = []
ALL_METHOD_NAMES = []
RPCS_STATUS = []
ALL_RPC_EXAMPLES = {}
GENERATE_EXAMPLES = True

FUND_WALLET_AMOUNT_SAT = 200000000
FUND_CHANNEL_AMOUNT_SAT = 10**6
LOG_FILE = './tests/autogenerate-examples-status.log'
EXAMPLES_JSON = {}
TEMP_EXAMPLES_FILE = './tests/autogenerate-examples.json'

NEW_VALUES_LIST = {
    'root_dir': '/root/lightning',
    'tmp_dir': '/tmp/.lightning',
    'tmp_reckless_val': '/tmp/reckless-0123456789abcdefg/',
    'checked_out_message': 'checked out HEAD: 012abc345def678ghi901jkl234mno567pqr89st',
    'str_1': '1',
    'num_1': 1,
    'balance_msat_1': 202500327000,
    'bytes_used': 1630000,
    'bytes_max': 10485760,
    'assocdata_1': 'assocdata0' + ('01' * 27),
    'hsm_secret_cdx_1': 'cl10leetsd35kw6r5de5kueedxyesqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqluplcg0lxenqd',
    'error_message_1': 'All addresses failed: 127.0.0.1:19736: Cryptographic handshake: peer closed connection (wrong key?). ',

    'blockheight_110': 110,
    'blockheight_130': 130,

    'script_pubkey_1': 'scriptpubkey' + ('01' * 28),
    'script_pubkey_2': 'scriptpubkey' + ('02' * 28),
    
    'onion_1': 'onion' + ('10' * 1363),
    'onion_2': 'onion' + ('20' * 1363),

    'shared_secrets_1': [
                'sharedsecret' + ('10' * 26),
                'sharedsecret' + ('11' * 26),
                'sharedsecret' + ('12' * 26)],
    'shared_secrets_2': [
                'sharedsecret' + ('20' * 26),
                'sharedsecret' + ('21' * 26),
                'sharedsecret' + ('22' * 26)],

    'invreq_id_1': 'invreqid' + ('01' * 28),
    'invreq_id_2': 'invreqid' + ('02' * 28),
    
    'invoice_1': 'lni1qqg0qe' + ('01' * 415),
    'invoice_2': 'lni1qqg0qe' + ('02' * 415),
    
    'funding_txid_1': 'fundingtxid001' + ('01' * 25),
    'funding_txid_2': 'fundingtxid002' + ('02' * 25),

    'signature_1': 'dcde30c4bb50bed221009d' + ('01' * 60),
    'signature_2': 'dcdepay30c4bb50bed209d' + ('02' * 60),

    'destination_1': 'bcrt1p52' + ('01' * 28),
    'destination_2': 'bcrt1qcqqv' + ('01' * 17),
    'destination_3': 'bcrt1phtprcvhz' + ('02' * 25),
    'destination_4': 'bcrt1p00' + ('02' * 28),
    'destination_5': 'bcrt1p00' + ('03' * 28),

    'funding_serial_1': 17725655605188060551,
    'funding_serial_2': 17725655605188060552,
    'funding_serial_3': 17725655605188060553,
    'funding_serial_4': 17725655605188060554,
    'funding_serial_5': 17725655605188060555,

    'l1_id': 'nodeid' + ('01' * 30),
    'l2_id': 'nodeid' + ('02' * 30),
    'l3_id': 'nodeid' + ('03' * 30),
    'l4_id': 'nodeid' + ('04' * 30),
    'l5_id': 'nodeid' + ('05' * 30),
    'l6_id': 'nodeid' + ('06' * 30),
    'l7_id': 'nodeid' + ('07' * 30),
    'l8_id': 'nodeid' + ('08' * 30),
    'l9_id': 'nodeid' + ('09' * 30),
    'l10_id': 'nodeid' + ('10' * 30),
    'l11_id': 'nodeid' + ('11' * 30),
    'l12_id': 'nodeid' + ('12' * 30),

	'l1_alias': 'JUNIORBEAM',
	'l2_alias': 'SILENTARTIST',
	'l3_alias': 'HOPPINGFIRE',
	'l4_alias': 'JUNIORFELONY',
	'l5_alias': 'SOMBERFIRE',
	'l6_alias': 'LOUDPHOTO',
    'l7_alias': 'SILENTTRINITY',
    'l8_alias': 'GREENPLOW',
    'l9_alias': 'SOMBERCHIPMUNK',
    'l10_alias': 'LIGHTNINGWALK',
    'l11_alias': 'SLICKERMONTANA',
    'l12_alias': 'STRANGEWAFFLE',

    'l1_port': 19734,
    'l2_port': 19735,
    'l3_port': 19736,
    'l4_port': 19737,
    'l5_port': 19738,
    'l6_port': 19739,
    'l7_port': 19740,
    'l8_port': 19741,
    'l9_port': 19742,
    'l10_port': 19743,
    'l11_port': 19744,
    'l12_port': 19745,

    'l1_addr': '127.0.0.1:19734',
    'l2_addr': '127.0.0.1:19735',
    'l3_addr': '127.0.0.1:19736',
    'l4_addr': '127.0.0.1:19737',
    'l5_addr': '127.0.0.1:19738',
    'l6_addr': '127.0.0.1:19739',
    'l7_addr': '127.0.0.1:19740',
    'l8_addr': '127.0.0.1:19741',
    'l9_addr': '127.0.0.1:19742',
    'l10_addr': '127.0.0.1:19743',
    'l11_addr': '127.0.0.1:19744',
    'l12_addr': '127.0.0.1:19745',

    'c12': '109x1x1',
    'c23': '111x1x1',
    'c24': '113x1x1',
    'c25': '115x1x1',
    'c34': '117x1x1',
    'c78': '142x1x1',

    'c12_tx': '020000000000102fundchanneltx' + ('12000' * 99),
    'c23_tx': '020000000000203fundchanneltx' + ('23000' * 99),
    'c24_tx': '020000000000204fundchanneltx' + ('24000' * 99),
    'c25_tx': '020000000000205fundchanneltx' + ('25000' * 99),
    'c34_tx': '020000000000304fundchanneltx' + ('34000' * 99),
    'c35_tx': '020000000000305fundchanneltx' + ('35000' * 99),
    'c41_tx': '020000000000401fundchanneltx' + ('41000' * 99),
    'c78_tx': '020000000000708fundchanneltx' + ('78000' * 99),
    'c1112_tx': '020000000001112fundchanneltx' + ('11120' * 99),
    'upgrade_tx': '02000000000101upgd' + ('20000' * 34),
    'close1_tx': '02000000000101cls0' + ('01' * 200),
    'close2_tx': '02000000000101cls1' + ('02' * 200),
    'send_tx_1': '02000000000101sendpt' + ('64000' * 100),
    'send_tx_2': '02000000000102sendpt' + ('65000' * 100),
    'tx_55': '02000000000155multiw' + ('55000' * 100),
    'tx_56': '02000000000155multiw' + ('56000' * 100),
    'tx_61': '02000000000155multiw' + ('61000' * 100),
    'tx_91': '020000000001wthdrw' + ('91000' * 100),
    'tx_92': '020000000002wthdrw' + ('92000' * 100),
    'unsigned_tx_1': '0200000000' + ('0002' * 66),
    'unsigned_tx_2': '0200000000' + ('0004' * 66),
    'unsigned_tx_3': '0200000000' + ('0006' * 66),
    'unsigned_tx_4': '0200000000' + ('0008' * 66),
    'multi_tx_1': '02000000000101multif' + ('50000' * 100),
    'multi_tx_2': '02000000000102multif' + ('60000' * 100),
    'ocs_tx_1': '02000000000101sgpsbt' + ('11000' * 100),
    'ocs_tx_2': '02000000000101sgpsbt' + ('12000' * 100),
    'txsend_tx_1': '02000000000101txsend' + ('00011' * 100),
    'txsend_tx_2': '02000000000101txsend' + ('00022' * 100),

    'c12_txid': 'channeltxid' + ('120000' * 9),
    'c23_txid': 'channeltxid' + ('230000' * 9),
    'c24_txid': 'channeltxid' + ('240000' * 9),
    'c25_txid': 'channeltxid' + ('250000' * 9),
    'c34_txid': 'channeltxid' + ('340000' * 9),
    'c35_txid': 'channeltxid' + ('350000' * 9),
    'c41_txid': 'channeltxid' + ('410000' * 9),
    'c78_txid': 'channeltxid' + ('780000' * 9),
    'c1112_txid': 'channeltxid' + ('111200' * 9),
    'upgrade_txid': 'txidupgrade' + ('200000' * 9),
    'close1_txid': 'txid' + ('01' * 30),
    'close2_txid': 'txid' + ('02' * 30),
    'send_txid_1': 'txid' + ('64000' * 11),
    'send_txid_2': 'txid' + ('65000' * 11),
    'txid_55': 'txid' + ('55000' * 11),
    'txid_56': 'txid' + ('56000' * 11),
    'txid_61': 'txid' + ('61000' * 11),
    'withdraw_txid_l21': 'txidwithdraw21' + ('91000' * 10),
    'withdraw_txid_l22': 'txidwithdraw22' + ('92000' * 10),
    'txprep_txid_1': 'txidtxprep0001' + ('00001' * 10),
    'txprep_txid_2': 'txidtxprep0002' + ('00002' * 10),
    'txprep_txid_3': 'txidtxprep0003' + ('00003' * 10),
    'txprep_txid_4': 'txidtxprep0004' + ('00004' * 10),
    'multi_txid_1': 'channeltxid010' + ('50000' * 10),
    'multi_txid_2': 'channeltxid020' + ('60000' * 10),
    'utxo_1': 'utxo' + ('01' * 30),
    'ocs_txid_1': 'txidocsigned10' + ('11000' * 10),
    'ocs_txid_2': 'txidocsigned10' + ('12000' * 10),
    'txsend_txid_1': 'txidtxsend1000' + ('00011' * 10),
    'txsend_txid_2': 'txidtxsend1000' + ('00022' * 10),
    
    'c12_channel_id': 'channelid0' + ('120000' * 9),
    'c23_channel_id': 'channelid0' + ('230000' * 9),
    'c24_channel_id': 'channelid0' + ('240000' * 9),
    'c25_channel_id': 'channelid0' + ('250000' * 9),
    'c34_channel_id': 'channelid0' + ('340000' * 9),
    'c35_channel_id': 'channelid0' + ('350000' * 9),
    'c41_channel_id': 'channelid0' + ('410000' * 9),
    'c78_channel_id': 'channelid0' + ('780000' * 9),
    'c1112_channel_id': 'channelid0' + ('111200' * 9),
    'c910_channel_id_1': 'channelid' + ('09101' * 11),
    'c910_channel_id_2': 'channelid' + ('09102' * 11),
    'mf_channel_id_1': 'channelid' + ('11000' * 11),
    'mf_channel_id_2': 'channelid' + ('12000' * 11),
    'mf_channel_id_3': 'channelid' + ('13000' * 11),
    'mf_channel_id_4': 'channelid' + ('15200' * 11),

    'time_at_110': 1731100000,
    'time_at_120': 1731200000,
    'time_at_130': 1731300000,
    'time_at_210': 1732100000,
    'time_at_220': 1732200000,
    'time_at_240': 1732400000,
    'time_at_250': 1732500000,
    'time_at_260': 1732600000,
    'time_at_330': 1733300000,
    'time_at_340': 1733400000,
    'time_at_700': 1737000000,
    'time_at_710': 1737100000,
    'time_at_760': 1737600000,
    'time_at_770': 1737700000,
    'time_at_780': 1737800000,
    'time_at_790': 1737900000,
    'time_at_800': 1738000000,
    'time_at_810': 1738100000,
    'time_at_820': 1738200000,
    'time_at_830': 1738300000,
    'time_at_840': 1738400000,
    'time_at_850': 1738500000,
    'time_at_860': 1738600000,
    'time_at_870': 1738700000,
    'time_at_990': 1739900000,

    'bolt11_l11': 'lnbcrt100n1pnt2' + ('bolt11invl010100000000' * 10),
    'bolt11_l12': 'lnbcrt100n1pnt2' + ('bolt11invl010200000000' * 10),
    'bolt11_l13': 'lnbcrt100n1pnt2' + ('bolt11invl010300000000' * 10),
    'bolt11_l21': 'lnbcrt100n1pnt2' + ('bolt11invl020100000000' * 10),
    'bolt11_l22': 'lnbcrt100n1pnt2' + ('bolt11invl020200000000' * 10),
    'bolt11_l23': 'lnbcrt100n1pnt2' + ('bolt11invl020300000000' * 10),
    'bolt11_l24': 'lnbcrt100n1pnt2' + ('bolt11invl020400000000' * 10),
    'bolt11_l25': 'lnbcrt100n1pnt2' + ('bolt11invl020500000000' * 10),
    'bolt11_l26': 'lnbcrt100n1pnt2' + ('bolt11invl020600000000' * 10),
    'bolt11_l31': 'lnbcrt100n1pnt2' + ('bolt11invl030100000000' * 10),
    'bolt11_l33': 'lnbcrt100n1pnt2' + ('bolt11invl030300000000' * 10),
    'bolt11_l34': 'lnbcrt100n1pnt2' + ('bolt11invl030400000000' * 10),
    'bolt11_l66': 'lnbcrt100n1pnt2' + ('bolt11invl060600000000' * 10),
    'bolt11_l67': 'lnbcrt100n1pnt2' + ('bolt11invl060700000000' * 10),
    'bolt11_wt_1': 'lnbcrt222n1pnt3005720bolt11wtinv' + ('01' * 160),
    'bolt11_wt_2': 'lnbcrt222n1pnt3005720bolt11wtinv' + ('02' * 160),
    'bolt11_di_1': 'lnbcrt222n1pnt3005720bolt11300' + ('01' * 170),
    'bolt11_di_2': 'lnbcrt222n1pnt3005720bolt11300' + ('01' * 170),
    'bolt11_dp_1': 'lnbcrt222n1pnt3005720bolt11400' + ('01' * 170),
    'bolt11_dp_2': 'lnbcrt222n1pnt3005720bolt11401' + ('02' * 170),

    'bolt12_l21': 'lno1qgsq000bolt' + ('21000' * 24),
    'bolt12_l22': 'lno1qgsq000bolt' + ('22000' * 24),
    'bolt12_l23': 'lno1qgsq000bolt' + ('23000' * 24),
    'bolt12_l24': 'lno1qgsq000bolt' + ('24000' * 24),
    'bolt12_si_1': 'lno1qgsq000bolt' + ('si100' * 24),

    'offerid_l21': 'offeridl' + ('2100000' * 8),
    'offerid_l22': 'offeridl' + ('2200000' * 8),
    'offerid_l23': 'offeridl' + ('2300000' * 8),

    'payment_hash_l11': 'paymenthashinvl0' + ('1100' * 12),
    'payment_hash_l12': 'paymenthashinvl0' + ('1200' * 12),
    'payment_hash_l13': 'paymenthashinvl0' + ('1300' * 12),
    'payment_hash_l21': 'paymenthashinvl0' + ('2100' * 12),
    'payment_hash_l22': 'paymenthashinvl0' + ('2200' * 12),
    'payment_hash_l31': 'paymenthashinvl0' + ('3100' * 12),
    'payment_hash_l24': 'paymenthashinvl0' + ('2400' * 12),
    'payment_hash_l25': 'paymenthashinvl0' + ('2500' * 12),
    'payment_hash_l26': 'paymenthashinvl0' + ('2600' * 12),
    'payment_hash_l33': 'paymenthashinvl0' + ('3300' * 12),
    'payment_hash_l34': 'paymenthashinvl0' + ('3400' * 12),
    'payment_hash_key_1': 'paymenthashkey01' + ('k101' * 12),
    'payment_hash_key_2': 'paymenthashkey02' + ('k201' * 12),
    'payment_hash_key_3': 'paymenthashkey03' + ('k301' * 12),
    'payment_hash_cmd_pay_1': 'paymenthashcmdpy' + ('cp10' * 12),
    'payment_hash_si_1': 'paymenthashsdinv' + ('si10' * 12),
    'payment_hash_wspc_1': 'paymenthashwtspct2' + ('01' * 23),
    'payment_hash_wsup_2': 'paymenthashwtspup2' + ('02' * 23),
    'payment_hash_winv_1': 'paymenthashwaitinv' + ('01' * 23),
    'payment_hash_winv_2': 'paymenthashwaitinv' + ('02' * 23),
    'payment_hash_di_1': 'paymenthashdelinv1' + ('01' * 23),
    'payment_hash_di_2': 'paymenthashdelinv2' + ('02' * 23),
    'payment_hash_dp_1': 'paymenthashdelpay1' + ('01' * 23),
    'payment_hash_dp_2': 'paymenthashdelpay2' + ('02' * 23),
    'payment_hash_dp_3': 'paymenthashdelpay3' + ('03' * 23),

    'payment_preimage_1': 'paymentpreimage1' + ('01' * 24),
    'payment_preimage_2': 'paymentpreimage2' + ('02' * 24),
    'payment_preimage_3': 'paymentpreimage3' + ('03' * 24),
    'payment_preimage_ep_1': 'paymentpreimagep' + ('01' * 24),
    'payment_preimage_ep_2': 'paymentpreimagep' + ('02' * 24),
    'payments_preimage_i_1': 'paymentpreimagei' + ('01' * 24),
    'payments_preimage_w_1': 'paymentpreimagew' + ('01' * 24),
    'payment_preimage_cmd_1': 'paymentpreimagec' + ('01' * 24),
    'payment_preimage_r_1': 'paymentpreimager' + ('01' * 24),
    'payment_preimage_r_2': 'paymentpreimager' + ('02' * 24),
    'payment_preimage_wi_1': 'paymentpreimagewaitinv0' + ('01' * 21),
    'payment_preimage_wi_2': 'paymentpreimagewaitinv0' + ('02' * 21),
    'payment_preimage_di_1': 'paymentpreimagedelinv01' + ('01' * 21),
    'payment_preimage_dp_1': 'paymentpreimgdp1' + ('01' * 24),

    'payment_secret_l11': 'paymentsecretinvl00' + ('11000' * 9),
    'payment_secret_l12': 'paymentsecretinvl00' + ('12000' * 9),
    'payment_secret_l13': 'paymentsecretinvl00' + ('13000' * 9),
    'payment_secret_l21': 'paymentsecretinvl00' + ('21000' * 9),
    'payment_secret_l22': 'paymentsecretinvl00' + ('22000' * 9),
    'payment_secret_l24': 'paymentsecretinvl00' + ('24000' * 9),
    'payment_secret_l25': 'paymentsecretinvl00' + ('25000' * 9),
    'payment_secret_l26': 'paymentsecretinvl00' + ('26000' * 9),
    'payment_secret_l31': 'paymentsecretinvl00' + ('31000' * 9),
    'payment_secret_l33': 'paymentsecretinvl00' + ('33000' * 9),
    'payment_secret_l34': 'paymentsecretinvl00' + ('34000' * 9),

    'init_psbt_1': 'cHNidP8BAgpsbt10' + ('01' * 52),
    'init_psbt_2': 'cHNidP8BAgpsbt20' + ('02' * 84),
    'init_psbt_3': 'cHNidP8BAgpsbt30' + ('03' * 92),
    'upgrade_psbt_1': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('110000' * 100),
    'psbt_1': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('711000' * 120),
    'psbt_2': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('712000' * 120),
    'psbt_3': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('713000' * 120),
    'psbt_4': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('714000' * 120),
    'psbt_5': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('715000' * 120),
    'psbt_6': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('716000' * 120),
    'psbt_7': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('911000' * 40),
    'psbt_8': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('922000' * 40),
    'psbt_9': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('101000' * 40),
    'psbt_10': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('201000' * 40),
    'psbt_11': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('301000' * 40),
    'psbt_12': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('401000' * 40),
    'psbt_13': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('310000' * 40),
    'psbt_14': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('410000' * 40),
    'psbt_15': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('510000' * 40),
    'psbt_16': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('520000' * 40),
    'psbt_17': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('610000' * 40),
    'psbt_18': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('710000' * 40),
    'psbt_19': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('810000' * 40),
    'psbt_20': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('910000' * 40),
    'psbt_21': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('101000' * 40),
    'psbt_22': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('111000' * 40),
    'psbt_23': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('121000' * 40),
    'psbt_24': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('011100' * 40),
    'psbt_25': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('011200' * 40),
    'psbt_26': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('022200' * 40),
    'signed_psbt_1': 'cHNidP8BAgQCAAAAAQMEbwAAAAEEAQpsbt' + ('718000' * 120), 
}

            
REPLACE_RESPONSE_VALUES = [
    { 'data_keys': ['any'], 'original_value': re.compile(re.escape(CWD)), 'new_value': NEW_VALUES_LIST['root_dir'] },
    { 'data_keys': ['any'], 'original_value': re.compile(r'/tmp/ltests-[^/]+/test_generate_examples_[^/]+/lightning-[^/]+'), 'new_value': NEW_VALUES_LIST['tmp_dir'] },
    { 'data_keys': ['any'], 'original_value': re.compile(r'/tmp/reckless-[\w]+/'), 'new_value': NEW_VALUES_LIST['tmp_reckless_val'] },
    { 'data_keys': ['any'], 'original_value': re.compile(r'checked out HEAD: [\da-f]+'), 'new_value': NEW_VALUES_LIST['checked_out_message'] },
    { 'data_keys': ['outnum', 'funding_outnum', 'vout'], 'original_value': '0', 'new_value': NEW_VALUES_LIST['str_1'] },
    { 'data_keys': ['outnum', 'funding_outnum', 'vout'], 'original_value': 0, 'new_value': NEW_VALUES_LIST['num_1'] },
    { 'data_keys': ['outnum', 'funding_outnum', 'vout'], 'original_value': 2, 'new_value': NEW_VALUES_LIST['num_1'] },
    { 'data_keys': ['outnum', 'funding_outnum', 'vout'], 'original_value': 3, 'new_value': NEW_VALUES_LIST['num_1'] },
]

if os.path.exists(LOG_FILE):
    open(LOG_FILE, 'w').close()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    datefmt='%H:%M:%S',
                    handlers=[
                        logging.FileHandler(LOG_FILE),
                        logging.StreamHandler()
                    ])

logger = logging.getLogger(__name__)


class TaskFinished(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


@pytest.fixture(autouse=True)
def canned_github_server(directory):
    global NETWORK
    NETWORK = os.environ.get('TEST_NETWORK')
    if NETWORK is None:
        NETWORK = 'regtest'
    FILE_PATH = Path(os.path.dirname(os.path.realpath(__file__)))
    if os.environ.get('LIGHTNING_CLI') is None:
        os.environ['LIGHTNING_CLI'] = str(FILE_PATH.parent / 'cli/lightning-cli')
    # Use socket to provision a random free port
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('localhost', 0))
    free_port = str(sock.getsockname()[1])
    sock.close()
    global my_env
    my_env = os.environ.copy()
    # This tells reckless to redirect to the canned server rather than github.
    my_env['REDIR_GITHUB_API'] = f'http://127.0.0.1:{free_port}/api'
    my_env['REDIR_GITHUB'] = directory
    my_env['FLASK_RUN_PORT'] = free_port
    my_env['FLASK_APP'] = str(FILE_PATH / 'rkls_github_canned_server')
    server = subprocess.Popen(["python3", "-m", "flask", "run"],
                              env=my_env)

    # Generate test plugin repository to test reckless against.
    repo_dir = os.path.join(directory, "lightningd")
    os.mkdir(repo_dir, 0o777)
    plugins_path = str(FILE_PATH / 'data/recklessrepo/lightningd')

    # Create requirements.txt file for the testpluginpass
    # with pyln-client installed from the local source
    requirements_file_path = os.path.join(plugins_path, 'testplugpass', 'requirements.txt')
    with open(requirements_file_path, 'w') as f:
        pyln_client_path = os.path.abspath(os.path.join(FILE_PATH, '..', 'contrib', 'pyln-client'))
        f.write(f"pyln-client @ file://{pyln_client_path}\n")

    # This lets us temporarily set .gitconfig user info in order to commit
    my_env['HOME'] = directory
    with open(os.path.join(directory, '.gitconfig'), 'w') as conf:
        conf.write(("[user]\n"
                    "\temail = reckless@example.com\n"
                    "\tname = reckless CI\n"
                    "\t[init]\n"
                    "\tdefaultBranch = master"))

    # Bare repository must be initialized prior to setting other git env vars
    subprocess.check_output(['git', 'init', '--bare', 'plugins'], cwd=repo_dir,
                            env=my_env)

    my_env['GIT_DIR'] = os.path.join(repo_dir, 'plugins')
    my_env['GIT_WORK_TREE'] = repo_dir
    my_env['GIT_INDEX_FILE'] = os.path.join(repo_dir, 'scratch-index')
    repo_initialization = (f'cp -r {plugins_path}/* .;'
                           'git add --all;'
                           'git commit -m "initial commit - autogenerated by test_reckless.py";')
    tag_and_update = ('git tag v1;'
                      "sed -i 's/v1/v2/g' testplugpass/testplugpass.py;"
                      'git add testplugpass/testplugpass.py;'
                      'git commit -m "update to v2";'
                      'git tag v2;')
    subprocess.check_output([repo_initialization], env=my_env, shell=True,
                            cwd=repo_dir)
    subprocess.check_output([tag_and_update], env=my_env,
                            shell=True, cwd=repo_dir)
    del my_env['HOME']
    del my_env['GIT_DIR']
    del my_env['GIT_WORK_TREE']
    del my_env['GIT_INDEX_FILE']
    # We also need the github api data for the repo which will be served via http
    shutil.copyfile(str(FILE_PATH / 'data/recklessrepo/rkls_api_lightningd_plugins.json'), os.path.join(directory, 'rkls_api_lightningd_plugins.json'))
    yield
    # Delete requirements.txt from the testplugpass directory
    with open(requirements_file_path, 'w') as f:
        f.write(f"pyln-client\n\n")
    server.terminate()


def reckless(cmds: list, dir: PosixPath = None, autoconfirm=True, timeout: int = 15):
    '''Call the reckless executable, optionally with a directory.'''
    if dir is not None:
        cmds.insert(0, "-l")
        cmds.insert(1, str(dir))
    cmds.insert(0, "tools/reckless")
    r = subprocess.run(cmds, capture_output=True, encoding='utf-8', env=my_env, input='Y\n')
    return r


def replace_values_in_json(data, data_key):
    if isinstance(data, dict):
        return {key: replace_values_in_json(value, key) for key, value in data.items()}
    elif isinstance(data, list):
        for replace_value in REPLACE_RESPONSE_VALUES:
            if 'data_keys' in replace_value and any(item == 'any' or item == data_key for item in replace_value['data_keys']) and data == replace_value['original_value']:
                data = replace_value['new_value']
                return data
        return [replace_values_in_json(item, 'listitem') for item in data]
    elif isinstance(data, str):
        for replace_value in REPLACE_RESPONSE_VALUES:
            if any(item == data_key for item in replace_value['data_keys']) and data == replace_value['original_value']:
                data = replace_value['new_value']
                break
            elif any(item == 'any' for item in replace_value['data_keys']) and isinstance(replace_value['original_value'], str) and data == replace_value['original_value']:
                data = data.replace(replace_value['original_value'], replace_value['new_value'])
                break
            elif replace_value['data_keys'] == ['any'] and isinstance(replace_value['original_value'], re.Pattern):
                if re.match(replace_value['original_value'], data):
                    data = replace_value['original_value'].sub(replace_value['new_value'], data)
                    break
        return data
    elif isinstance(data, (int, float)):
        for replace_value in REPLACE_RESPONSE_VALUES:
            if 'data_keys' in replace_value and any(item == 'any' or item == data_key for item in replace_value['data_keys']) and data == replace_value['original_value']:
                data = replace_value['new_value']
                break
        return data
    else:
        return data


def update_examples_in_schema_files():
    """Update examples in JSON schema files"""
    # For testing
    if os.path.exists(TEMP_EXAMPLES_FILE):
        open(TEMP_EXAMPLES_FILE, 'w').close()
    with open(TEMP_EXAMPLES_FILE, 'w+', encoding='utf-8') as file:
        json.dump({ 'replace_response_values': REPLACE_RESPONSE_VALUES[4:], 'examples_json': EXAMPLES_JSON }, file, indent=2, ensure_ascii=False)

    try:
        updated_examples = {}
        for method, method_examples in EXAMPLES_JSON.items():
            try:
                global CWD
                file_path = os.path.join(CWD, 'doc', 'schemas', f'lightning-{method}.json')
                logger.info(f'Updating examples for {method} in file {file_path}')
                with open(file_path, 'r+', encoding='utf-8') as file:
                    data = json.load(file)
                    updated_examples[method] = replace_values_in_json(method_examples, 'examples')['examples']
                    data['examples'] = updated_examples[method]
                    file.seek(0)
                    json.dump(data, file, indent=2, ensure_ascii=False)
                    file.write('\n')
                    file.truncate()
            except FileNotFoundError as fnf_error:
                logger.error(f'File not found error {fnf_error} for {file_path}')
            except Exception as e:
                logger.error(f'Error saving example in file {file_path}: {e}')
    except Exception as e:
        logger.error(f'Error updating examples in schema files: {e}')

    if os.path.exists(TEMP_EXAMPLES_FILE):
        open(TEMP_EXAMPLES_FILE, 'w').close()
    with open(TEMP_EXAMPLES_FILE, 'w+', encoding='utf-8') as file:
        json.dump({ 'replace_response_values': REPLACE_RESPONSE_VALUES[4:], 'examples_json': EXAMPLES_JSON, 'updated_examples_json': updated_examples }, file, indent=2, ensure_ascii=False)

    logger.info(f'Updated All Examples in Schema Files!')
    return None


def update_example(node, method, params, res=None, description=None, execute=True, filename=None):
    """Update examples with rpc calls and responses"""
    method_examples = EXAMPLES_JSON.get(method, { 'examples': [] })
    method_id = len(method_examples['examples']) + 1
    req = {
        'id': f'example:{method}#{method_id}',
        'method': method,
        'params': params
    }
    logger.info(f'Method \'{method}\', Params {params}')
    # Execute the RPC call and get the response
    if execute:
        res = node.rpc.call(method, params)
    logger.info(f'{method} response: {res}')
    # Return response without updating the file because user doesn't want to update the example
    # Executing the method and returning the response is useful for further example updates
    if method not in REGENERATING_RPCS:
        return res
    else:
        method_examples['examples'].append({'request': req, 'response': res} if description is None else {'description': description, 'request': req, 'response': res})
        EXAMPLES_JSON[method] = method_examples
    logger.info(f'Updated {method}#{method_id} example json')
    for rpc in ALL_RPC_EXAMPLES:
        if rpc['method'] == method:
            rpc['executed'] += 1
            if rpc['executed'] == rpc['num_examples']:
                RPCS_STATUS[REGENERATING_RPCS.index(method)] = True
            break
    # Exit if listed commands have been executed
    if all(RPCS_STATUS):
        raise TaskFinished('All Done!!!')
    return res


def setup_test_nodes(node_factory, bitcoind):
    """Sets up six test nodes for various transaction scenarios:
        l1, l2, l3 for transactions and forwards
        l4 for complex transactions (sendpayment, keysend, renepay)
        l5 for keysend with routehints and channel backup & recovery
        l5, l6 for backup and recovery
        l7, l8 for splicing (added later)
        l9, l10 for low level fundchannel examples (added later)
        l11, l12 for low level openchannel examples (added later)
        l13 for recover (added later)
        l1->l2, l2->l3, l3->l4, l2->l5 (unannounced), l9->l10, l11->l12
        l1.info['id']: 0266e4598d1d3c415f572a8488830b60f7e744ed9235eb0b1ba93283b315c03518
        l2.info['id']: 022d223620a359a47ff7f7ac447c85c46c923da53389221a0054c11c1e3ca31d59
        l3.info['id']: 035d2b1192dfba134e10e540875d366ebc8bc353d5aa766b80c090b39c3a5d885d
        l4.info['id']: 0382ce59ebf18be7d84677c2e35f23294b9992ceca95491fcf8a56c6cb2d9de199
        l5.info['id']: 032cf15d1ad9c4a08d26eab1918f732d8ef8fdc6abb9640bf3db174372c491304e
        l6.info['id']: 0265b6ab5ec860cd257865d61ef0bbf5b3339c36cbda8b26b74e7f1dca490b6518
    """
    try:
        global FUND_WALLET_AMOUNT_SAT, FUND_CHANNEL_AMOUNT_SAT
        options = [
            {
                'experimental-dual-fund': None,
                'experimental-offers': None,
                'may_reconnect': True,
                'dev-hsmd-no-preapprove-check': None,
                'allow-deprecated-apis': True,
                'allow_bad_gossip': True,
                'broken_log': '.*',    # plugin-topology: DEPRECATED API USED: *, lightningd-3: had memleak messages, lightningd: MEMLEAK:, lightningd: init_cupdate for unknown scid etc.
                'dev-bitcoind-poll': 3,    # Default 1; increased to avoid rpc failures
            }.copy()
            for i in range(6)
        ]
        l1, l2, l3, l4, l5, l6 = node_factory.get_nodes(6, opts=options)
        # Upgrade wallet
        # Write the data/p2sh_wallet_hsm_secret to the hsm_path, so node can spend funds at p2sh_wrapped_addr
        p2sh_wrapped_addr = '2N2V4ee2vMkiXe5FSkRqFjQhiS9hKqNytv3'
        update_example(node=l1, method='upgradewallet', params={})
        txid = bitcoind.rpc.sendtoaddress(p2sh_wrapped_addr, 20000000 / 10 ** 8)
        bitcoind.generate_block(1)
        l1.daemon.wait_for_log('Owning output .* txid {} CONFIRMED'.format(txid))
        # Doing it with 'reserved ok' should have 1. We use a big feerate so we can get over the RBF hump
        upgrade_res2 = update_example(node=l1, method='upgradewallet', params={'feerate': 'urgent', 'reservedok': True})

        # Fund node wallets for further transactions
        fund_nodes = [l1, l2, l3, l4, l5]
        for node in fund_nodes:
            node.fundwallet(FUND_WALLET_AMOUNT_SAT)
        # Connect nodes and fund channels
        getinfo_res2 = update_example(node=l2, method='getinfo', params={})
        update_example(node=l1, method='connect', params={'id': l2.info['id'], 'host': 'localhost', 'port': l2.daemon.port})
        update_example(node=l2, method='connect', params={'id': l3.info['id'], 'host': 'localhost', 'port': l3.daemon.port})
        l3.rpc.connect(l4.info['id'], 'localhost', l4.port)
        l2.rpc.connect(l5.info['id'], 'localhost', l5.port)
        c12, c12res = l1.fundchannel(l2, FUND_CHANNEL_AMOUNT_SAT)
        c23, c23res = l2.fundchannel(l3, FUND_CHANNEL_AMOUNT_SAT)
        c34, c34res = l3.fundchannel(l4, FUND_CHANNEL_AMOUNT_SAT)
        c25, c25res = l2.fundchannel(l5, announce_channel=False)
        mine_funding_to_announce(bitcoind, [l1, l2, l3, l4])
        l1.wait_channel_active(c12)
        l1.wait_channel_active(c23)
        l1.wait_channel_active(c34)
        # Balance these newly opened channels
        l1.rpc.pay(l2.rpc.invoice('500000sat', 'lbl balance l1 to l2', 'description send some sats l1 to l2')['bolt11'])
        l2.rpc.pay(l3.rpc.invoice('500000sat', 'lbl balance l2 to l3', 'description send some sats l2 to l3')['bolt11'])
        l2.rpc.pay(l5.rpc.invoice('500000sat', 'lbl balance l2 to l5', 'description send some sats l2 to l5')['bolt11'])
        l3.rpc.pay(l4.rpc.invoice('500000sat', 'lbl balance l3 to l4', 'description send some sats l3 to l4')['bolt11'])
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l1.info['id'], 'new_value': NEW_VALUES_LIST['l1_id'] },
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l2.info['id'], 'new_value': NEW_VALUES_LIST['l2_id'] },
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l3.info['id'], 'new_value': NEW_VALUES_LIST['l3_id'] },
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l4.info['id'], 'new_value': NEW_VALUES_LIST['l4_id'] },
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l5.info['id'], 'new_value': NEW_VALUES_LIST['l5_id'] },
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l6.info['id'], 'new_value': NEW_VALUES_LIST['l6_id'] },

            { 'data_keys': ['alias'], 'original_value': l1.info['alias'], 'new_value': NEW_VALUES_LIST['l1_alias'] },
            { 'data_keys': ['port'], 'original_value': l1.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l1_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l1.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l1_addr'] },
            { 'data_keys': ['alias'], 'original_value': l2.info['alias'], 'new_value': NEW_VALUES_LIST['l2_alias'] },
            { 'data_keys': ['port'], 'original_value': l2.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l2_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l2.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l2_addr'] },
            { 'data_keys': ['version'], 'original_value': l2.info['version'], 'new_value': l2.info['version'].split('-')[0] },
            { 'data_keys': ['blockheight'], 'original_value': getinfo_res2['blockheight'], 'new_value': NEW_VALUES_LIST['blockheight_110'] },
            { 'data_keys': ['alias'], 'original_value': l3.info['alias'], 'new_value': NEW_VALUES_LIST['l3_alias'] },
            { 'data_keys': ['port'], 'original_value': l3.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l3_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l3.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l3_addr'] },
            { 'data_keys': ['alias'], 'original_value': l4.info['alias'], 'new_value': NEW_VALUES_LIST['l4_alias'] },
            { 'data_keys': ['port'], 'original_value': l4.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l4_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l4.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l4_addr'] },
            { 'data_keys': ['alias'], 'original_value': l5.info['alias'], 'new_value': NEW_VALUES_LIST['l5_alias'] },
            { 'data_keys': ['port'], 'original_value': l5.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l5_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l5.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l5_addr'] },
            { 'data_keys': ['alias'], 'original_value': l6.info['alias'], 'new_value': NEW_VALUES_LIST['l6_alias'] },
            { 'data_keys': ['port'], 'original_value': l6.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l6_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l6.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l6_addr'] },

            { 'data_keys': ['scid', 'channel', 'short_channel_id', 'in_channel'], 'original_value': c12, 'new_value': NEW_VALUES_LIST['c12'] },
            { 'data_keys': ['tx'], 'original_value': c12res['tx'], 'new_value': NEW_VALUES_LIST['c12_tx'] },
            { 'data_keys': ['txid'], 'original_value': c12res['txid'], 'new_value': NEW_VALUES_LIST['c12_txid'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': c12res['channel_id'], 'new_value': NEW_VALUES_LIST['c12_channel_id'] },

            { 'data_keys': ['scid', 'channel'], 'original_value': c23, 'new_value': NEW_VALUES_LIST['c23'] },
            { 'data_keys': ['tx'], 'original_value': c23res['tx'], 'new_value': NEW_VALUES_LIST['c23_tx'] },
            { 'data_keys': ['txid'], 'original_value': c23res['txid'], 'new_value': NEW_VALUES_LIST['c23_txid'] },
            { 'data_keys': ['channel_id', 'account', 'originating_account'], 'original_value': c23res['channel_id'], 'new_value': NEW_VALUES_LIST['c23_channel_id'] },

            { 'data_keys': ['scid', 'channel'], 'original_value': c34, 'new_value': NEW_VALUES_LIST['c34'] },
            { 'data_keys': ['tx'], 'original_value': c34res['tx'], 'new_value': NEW_VALUES_LIST['c34_tx'] },
            { 'data_keys': ['txid'], 'original_value': c34res['txid'], 'new_value': NEW_VALUES_LIST['c34_txid'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': c34res['channel_id'], 'new_value': NEW_VALUES_LIST['c34_channel_id'] },

            { 'data_keys': ['scid', 'channel', 'short_channel_id', 'id'], 'original_value': c25, 'new_value': NEW_VALUES_LIST['c25'] },
            { 'data_keys': ['tx'], 'original_value': c25res['tx'], 'new_value': NEW_VALUES_LIST['c25_tx'] },
            { 'data_keys': ['txid'], 'original_value': c25res['txid'], 'new_value': NEW_VALUES_LIST['c25_txid'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': c25res['channel_id'], 'new_value': NEW_VALUES_LIST['c25_channel_id'] },

            { 'data_keys': ['tx'], 'original_value': upgrade_res2['tx'], 'new_value': NEW_VALUES_LIST['upgrade_tx'] },
            { 'data_keys': ['txid'], 'original_value': upgrade_res2['txid'], 'new_value': NEW_VALUES_LIST['upgrade_txid'] },
            { 'data_keys': ['initialpsbt', 'psbt', 'signed_psbt'], 'original_value': upgrade_res2['psbt'], 'new_value': NEW_VALUES_LIST['upgrade_psbt_1'] },
        ])
        return l1, l2, l3, l4, l5, l6, c12, c23, c25, c34, c23res
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in setting up nodes: {e}')


def generate_transactions_examples(l1, l2, l3, l4, l5, c25, bitcoind):
    """Generate examples for various transactions and forwards"""
    try:
        logger.info('Simple Transactions Start...')
        global FUND_CHANNEL_AMOUNT_SAT
        # Simple Transactions by creating invoices, paying invoices, keysends
        inv_l31 = update_example(node=l3, method='invoice', params={'amount_msat': 10**4, 'label': 'lbl_l31', 'description': 'Invoice description l31'})
        route_l1_l3 = update_example(node=l1, method='getroute', params={'id': l3.info['id'], 'amount_msat': 10**4, 'riskfactor': 1})['route']
        inv_l32 = update_example(node=l3, method='invoice', params={'amount_msat': '50000msat', 'label': 'lbl_l32', 'description': 'l32 description'})
        route_l2_l4 = update_example(node=l2, method='getroute', params={'id': l4.info['id'], 'amount_msat': 500000, 'riskfactor': 10, 'cltv': 9})['route']
        sendpay_res1 = update_example(node=l1, method='sendpay', params={'route': route_l1_l3, 'payment_hash': inv_l31['payment_hash'], 'payment_secret': inv_l31['payment_secret']})
        waitsendpay_res1 = update_example(node=l1, method='waitsendpay', params={'payment_hash': inv_l31['payment_hash']})
        keysend_res1 = update_example(node=l1, method='keysend', params={'destination': l3.info['id'], 'amount_msat': 10000})
        keysend_res2 = update_example(node=l1, method='keysend', params={'destination': l4.info['id'], 'amount_msat': 10000000, 'extratlvs': {'133773310': '68656c6c6f776f726c64', '133773312': '66696c7465726d65'}})
        scid = only_one([channel for channel in l2.rpc.listpeerchannels()['channels'] if channel['peer_id'] == l3.info['id']])['alias']['remote']
        routehints = [[{
            'scid': scid,
            'id': l2.info['id'],
            'feebase': '1msat',
            'feeprop': 10,
            'expirydelta': 9,
        }]]
        keysend_res3 = update_example(node=l1, method='keysend', params={'destination': l3.info['id'], 'amount_msat': 10000, 'routehints': routehints})
        inv_l11 = l1.rpc.invoice('10000msat', 'lbl_l11', 'l11 description')
        inv_l21 = l2.rpc.invoice('any', 'lbl_l21', 'l21 description')
        inv_l22 = l2.rpc.invoice('200000msat', 'lbl_l22', 'l22 description')
        inv_l33 = l3.rpc.invoice('100000msat', 'lbl_l33', 'l33 description')
        inv_l34 = l3.rpc.invoice(4000, 'failed', 'failed description')
        pay_res1 = update_example(node=l1, method='pay', params=[inv_l32['bolt11']])
        pay_res2 = update_example(node=l2, method='pay', params={'bolt11': inv_l33['bolt11']})

        # Hops, create and send onion for onion routing
        def truncate_encode(i: int):
            """Encode a tu64 (or tu32 etc) value"""
            try:
                ret = struct.pack("!Q", i)
                while ret.startswith(b'\0'):
                    ret = ret[1:]
                return ret
            except Exception as e:
                logger.error(f'Error in encoding: {e}')

        def serialize_payload_tlv(n, blockheight: int = 0):
            """Serialize payload according to BOLT #4: Onion Routing Protocol"""
            try:
                block, tx, out = n['channel'].split('x')
                payload = TlvPayload()
                b = BytesIO()
                b.write(truncate_encode(int(n['amount_msat'])))
                payload.add_field(2, b.getvalue())
                b = BytesIO()
                b.write(truncate_encode(blockheight + n['delay']))
                payload.add_field(4, b.getvalue())
                b = BytesIO()
                b.write(struct.pack("!Q", int(block) << 40 | int(tx) << 16 | int(out)))
                payload.add_field(6, b.getvalue())
                return payload.to_bytes().hex()
            except Exception as e:
                logger.error(f'Error in serializing payload: {e}')

        def serialize_payload_final_tlv(n, payment_secret: str, blockheight: int = 0):
            """Serialize the last payload according to BOLT #4: Onion Routing Protocol"""
            try:
                payload = TlvPayload()
                b = BytesIO()
                b.write(truncate_encode(int(n['amount_msat'])))
                payload.add_field(2, b.getvalue())
                b = BytesIO()
                b.write(truncate_encode(blockheight + n['delay']))
                payload.add_field(4, b.getvalue())
                b = BytesIO()
                b.write(bytes.fromhex(payment_secret))
                b.write(truncate_encode(int(n['amount_msat'])))
                payload.add_field(8, b.getvalue())
                return payload.to_bytes().hex()
            except Exception as e:
                logger.error(f'Error in serializing final payload: {e}')

        blockheight = l1.rpc.getinfo()['blockheight']
        amt = 10**3
        route = l1.rpc.getroute(l4.info['id'], amt, 10)['route']
        inv = l4.rpc.invoice(amt, "lbl l4", "desc l4")
        first_hop = route[0]
        hops = []
        example_hops = []
        i = 1
        for h, n in zip(route[:-1], route[1:]):
            hops.append({'pubkey': h['id'], 'payload': serialize_payload_tlv(n, blockheight)})
            example_hops.append({ 'pubkey': h['id'], 'payload': 'payload0' + ((str(i) + '0') * 13) })
            i += 1
        hops.append({'pubkey': route[-1]['id'], 'payload': serialize_payload_final_tlv(route[-1], inv['payment_secret'], blockheight)})
        example_hops.append({ 'pubkey': route[-1]['id'], 'payload': 'payload0' + ((str(i) + '0') * 13) })
        onion_res1 = update_example(node=l1, method='createonion', params={'hops': hops, 'assocdata': inv['payment_hash']})
        onion_res2 = update_example(node=l1, method='createonion', params={'hops': hops, 'assocdata': inv['payment_hash'], 'session_key': '41' * 32})
        sendonion_res1 = update_example(node=l1, method='sendonion', params={'onion': onion_res1['onion'], 'first_hop': first_hop, 'payment_hash': inv['payment_hash']})
        l1.rpc.waitsendpay(payment_hash=inv['payment_hash'])

        # Close channels examples
        close_res1 = update_example(node=l2, method='close', params={'id': l3.info['id'], 'unilateraltimeout': 1})
        close_res2 = update_example(node=l3, method='close', params={'id': l4.info['id'], 'destination': l4.rpc.newaddr()['bech32']})
        bitcoind.generate_block(1)
        sync_blockheight(bitcoind, [l1, l2, l3, l4])

        # Channel 2 to 3 is closed, l1->l3 payment will fail where `failed` forward will be saved on l2
        l1.rpc.sendpay(route_l1_l3, inv_l34['payment_hash'], payment_secret=inv_l34['payment_secret'])
        with pytest.raises(RpcError):
            l1.rpc.waitsendpay(inv_l34['payment_hash'])

        # Reopen channels for further examples
        c23, c23res = l2.fundchannel(l3, FUND_CHANNEL_AMOUNT_SAT)
        c34, c34res = l3.fundchannel(l4, FUND_CHANNEL_AMOUNT_SAT)
        mine_funding_to_announce(bitcoind, [l3, l4])
        l2.wait_channel_active(c23)
        update_example(node=l2, method='setchannel', params={'id': c23, 'ignorefeelimits': True})
        update_example(node=l2, method='setchannel', params={'id': c25, 'feebase': 4000, 'feeppm': 300, 'enforcedelay': 0})

        # Some more invoices for signing and preapproving
        inv_l12 = l1.rpc.invoice(1000, 'label inv_l12', 'description inv_l12')
        inv_l24 = l2.rpc.invoice(123000, 'label inv_l24', 'description inv_l24', 3600)
        inv_l25 = l2.rpc.invoice(124000, 'label inv_l25', 'description inv_l25', 3600)
        inv_l26 = l2.rpc.invoice(125000, 'label inv_l26', 'description inv_l26', 3600)
        signinv_res1 = update_example(node=l2, method='signinvoice', params={'invstring': inv_l12['bolt11']})
        signinv_res2 = update_example(node=l3, method='signinvoice', params=[inv_l26['bolt11']])
        update_example(node=l1, method='preapprovekeysend', params={'destination': l2.info['id'], 'payment_hash': '00' * 32, 'amount_msat': 1000})
        update_example(node=l5, method='preapprovekeysend', params=[l5.info['id'], '01' * 32, 2000])
        update_example(node=l1, method='preapproveinvoice', params={'bolt11': inv_l24['bolt11']})
        update_example(node=l1, method='preapproveinvoice', params=[inv_l25['bolt11']])
        inv_req = update_example(node=l2, method='invoicerequest', params={'amount': 1000000, 'description': 'Simple test'})
        sendinvoice_res1 = update_example(node=l1, method='sendinvoice', params={'invreq': inv_req['bolt12'], 'label': 'test sendinvoice'})
        inv_l13 = l1.rpc.invoice(amount_msat=100000, label='lbl_l13', description='l13 description', preimage='01' * 32)
        createinv_res1 = update_example(node=l2, method='createinvoice', params={'invstring': inv_l13['bolt11'], 'label': 'lbl_l13', 'preimage': '01' * 32})
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['scid', 'channel'], 'original_value': route_l1_l3[0]['channel'], 'new_value': NEW_VALUES_LIST['c12'] },
            { 'data_keys': ['scid', 'channel'], 'original_value': route_l2_l4[0]['channel'], 'new_value': NEW_VALUES_LIST['c23'] },
            
            { 'data_keys': ['tx'], 'original_value': close_res1['tx'], 'new_value':  NEW_VALUES_LIST['close1_tx'] },
            { 'data_keys': ['txid', 'spending_txid'], 'original_value': close_res1['txid'], 'new_value': NEW_VALUES_LIST['close1_txid'] },
            { 'data_keys': ['tx'], 'original_value': close_res2['tx'], 'new_value': NEW_VALUES_LIST['close2_tx'] },
            { 'data_keys': ['txid'], 'original_value': close_res2['txid'], 'new_value': NEW_VALUES_LIST['close2_txid'] },

            { 'data_keys': ['any', 'bolt11'], 'original_value': createinv_res1['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l21'] },
            { 'data_keys': ['payment_hash'], 'original_value': createinv_res1['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l21'] },
            { 'data_keys': ['expires_at'], 'original_value': createinv_res1['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_800'] },

            { 'data_keys': ['payment_hash'], 'original_value': inv_l31['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l31'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l31['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l31'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l31['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l31'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l31['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_110'] },
            { 'data_keys': ['payment_hash'], 'original_value': inv_l32['payment_hash'], 'new_value': 'paymenthashinvl0' + ('3200' * 12) },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l32['bolt11'], 'new_value': 'lnbcrt100n1pnt2' + ('bolt11invl032000000000' * 10) },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l32['payment_secret'], 'new_value': 'paymentsecretinvl000' + ('3200' * 11) },
            { 'data_keys': ['expires_at'], 'original_value': inv_l32['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_110'] },
            { 'data_keys': ['scid', 'channel'], 'original_value': scid, 'new_value': NEW_VALUES_LIST['c23'] },
            { 'data_keys': ['payment_hash'], 'original_value': inv_l11['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l11'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l11['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l11'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l11['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l11'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l11['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_110'] },
            { 'data_keys': ['payment_hash'], 'original_value': inv_l21['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l21'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l21['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l21'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l21['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l21'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l21['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_210'] },
            { 'data_keys': ['payment_hash'], 'original_value': inv_l22['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l22'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l22['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l22'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l22['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l22'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l22['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_220'] },
            { 'data_keys': ['payment_hash'], 'original_value': inv_l33['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l33'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l33['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l33'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l33['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l33'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l33['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_330'] },
            { 'data_keys': ['payment_hash'], 'original_value': inv_l34['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l34'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l34['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l34'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l34['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l34'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l34['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_340'] },
            { 'data_keys': ['hops'], 'original_value': hops, 'new_value': example_hops },
            { 'data_keys': ['any', 'assocdata'], 'original_value': inv['payment_hash'], 'new_value': NEW_VALUES_LIST['assocdata_1'] },
            { 'data_keys': ['onion'], 'original_value': onion_res1['onion'], 'new_value': NEW_VALUES_LIST['onion_1'] },
            { 'data_keys': ['shared_secrets'], 'original_value': onion_res1['shared_secrets'], 'new_value': NEW_VALUES_LIST['shared_secrets_1'] },
            { 'data_keys': ['onion'], 'original_value': onion_res2['onion'], 'new_value': NEW_VALUES_LIST['onion_2'] },
            { 'data_keys': ['shared_secrets'], 'original_value': onion_res2['shared_secrets'], 'new_value': NEW_VALUES_LIST['shared_secrets_2'] },
            { 'data_keys': ['scid', 'channel', 'short_channel_id', 'id'], 'original_value': c23, 'new_value': NEW_VALUES_LIST['c23'] },
            { 'data_keys': ['tx'], 'original_value': c23res['tx'], 'new_value': NEW_VALUES_LIST['c23_tx'] },
            { 'data_keys': ['txid'], 'original_value': c23res['txid'], 'new_value': NEW_VALUES_LIST['c23_txid'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': c23res['channel_id'], 'new_value': NEW_VALUES_LIST['c23_channel_id'] },

            { 'data_keys': ['scid', 'channel'], 'original_value': c34, 'new_value': NEW_VALUES_LIST['c34'] },
            { 'data_keys': ['tx'], 'original_value': c34res['tx'], 'new_value': NEW_VALUES_LIST['c34_tx'] },
            { 'data_keys': ['txid'], 'original_value': c34res['txid'], 'new_value': NEW_VALUES_LIST['c34_txid'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': c34res['channel_id'], 'new_value': NEW_VALUES_LIST['c34_channel_id'] },
            { 'data_keys': ['payment_hash'], 'original_value': inv_l12['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l12'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l12['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l12'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l12['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l12'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l12['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_120'] },

            { 'data_keys': ['payment_hash'], 'original_value': inv_l24['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l24'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l24['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l24'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l24['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l24'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l24['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_240'] },

            { 'data_keys': ['payment_hash'], 'original_value': inv_l25['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l25'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l25['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l25'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l25['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l25'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l25['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_250'] },

            { 'data_keys': ['payment_hash'], 'original_value': inv_l26['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l26'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l26['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l26'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l26['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l26'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l26['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_260'] },
            { 'data_keys': ['payment_hash'], 'original_value': inv_l13['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_l13'] },
            { 'data_keys': ['any', 'invstring', 'bolt11'], 'original_value': inv_l13['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l13'] },
            { 'data_keys': ['payment_secret'], 'original_value': inv_l13['payment_secret'], 'new_value': NEW_VALUES_LIST['payment_secret_l13'] },
            { 'data_keys': ['expires_at'], 'original_value': inv_l13['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_130'] },
            
            { 'data_keys': ['invreq_id'], 'original_value': inv_req['invreq_id'], 'new_value': NEW_VALUES_LIST['invreq_id_1'] },
            { 'data_keys': ['any', 'bolt12', 'invreq'], 'original_value': inv_req['bolt12'], 'new_value': NEW_VALUES_LIST['bolt12_l21'] },
            
            { 'data_keys': ['payment_hash'], 'original_value': keysend_res1['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_key_1'] },
            { 'data_keys': ['created_at'], 'original_value': keysend_res1['created_at'], 'new_value': NEW_VALUES_LIST['time_at_790'] },
            { 'data_keys': ['payment_preimage'], 'original_value': keysend_res1['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_1'] },
            { 'data_keys': ['payment_hash'], 'original_value': keysend_res2['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_key_2'] },
            { 'data_keys': ['created_at'], 'original_value': keysend_res2['created_at'], 'new_value': NEW_VALUES_LIST['time_at_800'] },
            { 'data_keys': ['payment_preimage'], 'original_value': keysend_res2['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_2'] },
            { 'data_keys': ['payment_hash'], 'original_value': keysend_res3['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_key_3'] },
            { 'data_keys': ['created_at'], 'original_value': keysend_res3['created_at'], 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['payment_preimage'], 'original_value': keysend_res3['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_3'] },
        
            { 'data_keys': ['created_at'], 'original_value': pay_res1['created_at'], 'new_value': NEW_VALUES_LIST['time_at_800'] },
            { 'data_keys': ['payment_preimage'], 'original_value': pay_res1['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_ep_1'] },
            { 'data_keys': ['created_at'], 'original_value': pay_res2['created_at'], 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['payment_preimage'], 'original_value': pay_res2['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_ep_2'] },
            
            { 'data_keys': ['any', 'bolt12', 'invreq'], 'original_value': sendinvoice_res1['bolt12'], 'new_value': NEW_VALUES_LIST['bolt12_si_1'] },
            { 'data_keys': ['payment_hash'], 'original_value': sendinvoice_res1['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_si_1'] },
            { 'data_keys': ['payment_preimage'], 'original_value': sendinvoice_res1['payment_preimage'], 'new_value': NEW_VALUES_LIST['payments_preimage_i_1'] },
            { 'data_keys': ['paid_at'], 'original_value': sendinvoice_res1['paid_at'], 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['expires_at'], 'original_value': sendinvoice_res1['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_990'] },
            
            { 'data_keys': ['created_at'], 'original_value': sendonion_res1['created_at'], 'new_value': NEW_VALUES_LIST['time_at_850'] },
            { 'data_keys': ['created_at'], 'original_value': sendpay_res1['created_at'], 'new_value': NEW_VALUES_LIST['time_at_860'] },

            { 'data_keys': ['any', 'bolt11'], 'original_value': signinv_res1['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l66'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': signinv_res2['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l67'] },
            
            { 'data_keys': ['payment_preimage'], 'original_value': waitsendpay_res1['payment_preimage'], 'new_value': NEW_VALUES_LIST['payments_preimage_w_1'] },
            { 'data_keys': ['created_at'], 'original_value': waitsendpay_res1['created_at'], 'new_value': NEW_VALUES_LIST['time_at_860'] },
            { 'data_keys': ['completed_at'], 'original_value': waitsendpay_res1['completed_at'], 'new_value': NEW_VALUES_LIST['time_at_870'] },

        ])
        logger.info('Simple Transactions Done!')
        return inv_l11, inv_l21, inv_l22, inv_l31, inv_l32, inv_l34
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating transactions examples: {e}')


def generate_runes_examples(l1, l2, l3):
    """Covers all runes related examples"""
    try:
        logger.info('Runes Start...')
        # Runes
        trimmed_id = l1.info['id'][:20]
        rune_l21 = update_example(node=l2, method='createrune', params={}, description=['This creates a fresh rune which can do anything:'])
        rune_l22 = update_example(node=l2, method='createrune', params={'rune': rune_l21['rune'], 'restrictions': 'readonly'},
                                  description=['We can add restrictions to that rune, like so:',
                                               '',
                                               'The `readonly` restriction is a short-cut for two restrictions:',
                                               '',
                                               '1: `[\'method^list\', \'method^get\', \'method=summary\']`: You may call list, get or summary.',
                                               '',
                                               '2: `[\'method/listdatastore\']`: But not listdatastore: that contains sensitive stuff!'])
        update_example(node=l2, method='createrune', params={'rune': rune_l21['rune'], 'restrictions': [['method^list', 'method^get', 'method=summary'], ['method/listdatastore']]}, description=['We can do the same manually (readonly), like so:'])
        rune_l23 = update_example(node=l2, method='createrune', params={'restrictions': [[f'id^{trimmed_id}'], ['method=listpeers']]}, description=[f'This will allow the rune to be used for id starting with {trimmed_id}, and for the method listpeers:'])
        rune_l24 = update_example(node=l2, method='createrune', params={'restrictions': [['method=pay'], ['pnameamountmsat<10000']]}, description=['This will allow the rune to be used for the method pay, and for the parameter amount\\_msat to be less than 10000:'])
        update_example(node=l2, method='createrune', params={'restrictions': [[f'id={l1.info["id"]}'], ['method=listpeers'], ['pnum=1'], [f'pnameid={l1.info["id"]}', f'parr0={l1.info["id"]}']]}, description=["Let's create a rune which lets a specific peer run listpeers on themselves:"])
        rune_l25 = update_example(node=l2, method='createrune', params={'restrictions': [[f'id={l1.info["id"]}'], ['method=listpeers'], ['pnum=1'], [f'pnameid^{trimmed_id}', f'parr0^{trimmed_id}']]}, description=["This allows `listpeers` with 1 argument (`pnum=1`), which is either by name (`pnameid`), or position (`parr0`). We could shorten this in several ways: either allowing only positional or named parameters, or by testing the start of the parameters only. Here's an example which only checks the first 10 bytes of the `listpeers` parameter:"])
        update_example(node=l2, method='createrune', params=[rune_l25['rune'], [['time<"$(($(date +%s) + 24*60*60))"', 'rate=2']]], description=["Before we give this to our peer, let's add two more restrictions: that it only be usable for 24 hours from now (`time<`), and that it can only be used twice a minute (`rate=2`). `date +%s` can give us the current time in seconds:"])
        update_example(node=l2, method='commando-listrunes', params={'rune': rune_l23['rune']})
        update_example(node=l2, method='commando-listrunes', params={})
        commando_res1 = update_example(node=l1, method='commando', params={'peer_id': l2.info['id'], 'rune': rune_l22['rune'], 'method': 'getinfo', 'params': {}})
        commando_res2 = update_example(node=l1, method='commando', params={'peer_id': l2.info['id'], 'rune': rune_l23['rune'], 'method': 'listpeers', 'params': [l3.info['id']]})
        inv_l23 = l2.rpc.invoice('any', 'lbl_l23', 'l23 description')
        commando_res3 = update_example(node=l1, method='commando', params={'peer_id': l2.info['id'], 'rune': rune_l24['rune'], 'method': 'pay', 'params': {'bolt11': inv_l23['bolt11'], 'amount_msat': 9900}})
        update_example(node=l2, method='checkrune', params={'nodeid': l2.info['id'], 'rune': rune_l22['rune'], 'method': 'listpeers', 'params': {}})
        update_example(node=l2, method='checkrune', params={'nodeid': l2.info['id'], 'rune': rune_l24['rune'], 'method': 'pay', 'params': {'amount_msat': 9999}})
        showrunes_res1 = update_example(node=l2, method='showrunes', params={'rune': rune_l21['rune']})
        showrunes_res2 = update_example(node=l2, method='showrunes', params={})
        update_example(node=l2, method='commando-blacklist', params={'start': 1})
        update_example(node=l2, method='commando-blacklist', params={'start': 2, 'end': 3})
        update_example(node=l2, method='blacklistrune', params={'start': 1})
        update_example(node=l2, method='blacklistrune', params={'start': 0, 'end': 2})
        update_example(node=l2, method='blacklistrune', params={'start': 3, 'end': 4})

        # Commando runes
        rune_l11 = update_example(node=l1, method='commando-rune', params={}, description=['This creates a fresh rune which can do anything:'])
        update_example(node=l1, method='commando-rune', params={'rune': rune_l11['rune'], 'restrictions': 'readonly'},
                       description=['We can add restrictions to that rune, like so:',
                                    '',
                                    'The `readonly` restriction is a short-cut for two restrictions:',
                                    '',
                                    '1: `[\'method^list\', \'method^get\', \'method=summary\']`: You may call list, get or summary.',
                                    '',
                                    '2: `[\'method/listdatastore\']`: But not listdatastore: that contains sensitive stuff!'])
        update_example(node=l1, method='commando-rune', params={'rune': rune_l11['rune'], 'restrictions': [['method^list', 'method^get', 'method=summary'], ['method/listdatastore']]}, description=['We can do the same manually (readonly), like so:'])
        update_example(node=l1, method='commando-rune', params={'restrictions': [[f'id^{trimmed_id}'], ['method=listpeers']]}, description=[f'This will allow the rune to be used for id starting with {trimmed_id}, and for the method listpeers:'])
        update_example(node=l1, method='commando-rune', params={'restrictions': [['method=pay'], ['pnameamountmsat<10000']]}, description=['This will allow the rune to be used for the method pay, and for the parameter amount\\_msat to be less than 10000:'])
        update_example(node=l1, method='commando-rune', params={'restrictions': [[f'id={l1.info["id"]}'], ['method=listpeers'], ['pnum=1'], [f'pnameid={l1.info["id"]}', f'parr0={l1.info["id"]}']]}, description=["Let's create a rune which lets a specific peer run listpeers on themselves:"])
        rune_l15 = update_example(node=l1, method='commando-rune', params={'restrictions': [[f'id={l1.info["id"]}'], ['method=listpeers'], ['pnum=1'], [f'pnameid^{trimmed_id}', f'parr0^{trimmed_id}']]}, description=["This allows `listpeers` with 1 argument (`pnum=1`), which is either by name (`pnameid`), or position (`parr0`). We could shorten this in several ways: either allowing only positional or named parameters, or by testing the start of the parameters only. Here's an example which only checks the first 10 bytes of the `listpeers` parameter:"])
        update_example(node=l1, method='commando-rune', params=[rune_l15['rune'], [['time<"$(($(date +%s) + 24*60*60))"', 'rate=2']]], description=["Before we give this to our peer, let's add two more restrictions: that it only be usable for 24 hours from now (`time<`), and that it can only be used twice a minute (`rate=2`). `date +%s` can give us the current time in seconds:"])
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['last_used'], 'original_value': showrunes_res1['runes'][0]['last_used'], 'new_value': NEW_VALUES_LIST['time_at_760'] },
            { 'data_keys': ['last_used'], 'original_value': showrunes_res2['runes'][0]['last_used'], 'new_value': NEW_VALUES_LIST['time_at_770'] },
            { 'data_keys': ['last_used'], 'original_value': showrunes_res2['runes'][1]['last_used'], 'new_value': NEW_VALUES_LIST['time_at_780'] },
            { 'data_keys': ['last_used'], 'original_value': showrunes_res2['runes'][2]['last_used'], 'new_value': NEW_VALUES_LIST['time_at_790'] },

            { 'data_keys': ['any', 'bolt11'], 'original_value': inv_l23['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_l23'] },
            { 'data_keys': ['blockheight'], 'original_value': commando_res1['blockheight'], 'new_value': NEW_VALUES_LIST['blockheight_130'] },
            { 'data_keys': ['netaddr'], 'original_value': commando_res2['peers'][0]['netaddr'], 'new_value': [NEW_VALUES_LIST['l3_addr']] },
            { 'data_keys': ['created_at'], 'original_value': commando_res3['created_at'], 'new_value': NEW_VALUES_LIST['time_at_700'] },
            { 'data_keys': ['payment_hash'], 'original_value': commando_res3['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_cmd_pay_1'] },
            { 'data_keys': ['payment_preimage'], 'original_value': commando_res3['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_cmd_1'] },
        ])
        logger.info('Runes Done!')
        return rune_l21
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating runes examples: {e}')


def generate_datastore_examples(l2):
    """Covers all datastore related examples"""
    try:
        logger.info('Datastore Start...')
        update_example(node=l2, method='datastore', params={'key': 'somekey', 'hex': '61', 'mode': 'create-or-append'})
        update_example(node=l2, method='datastore', params={'key': ['test', 'name'], 'string': 'saving data to the store', 'mode': 'must-create'})
        update_example(node=l2, method='datastore', params={'key': 'otherkey', 'string': 'foo', 'mode': 'must-create'})
        update_example(node=l2, method='datastore', params={'key': 'otherkey', 'string': 'bar', 'mode': 'must-append', 'generation': 0})
        update_example(node=l2, method='datastoreusage', params={})
        update_example(node=l2, method='datastoreusage', params={'key': ['test', 'name']})
        update_example(node=l2, method='datastoreusage', params={'key': 'otherkey'})
        update_example(node=l2, method='deldatastore', params={'key': ['test', 'name']})
        update_example(node=l2, method='deldatastore', params={'key': 'otherkey', 'generation': 1})
        logger.info('Datastore Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating datastore examples: {e}')


def generate_bookkeeper_examples(l2, l3, c23_chan_id):
    """Generates all bookkeeper rpc examples"""
    try:
        logger.info('Bookkeeper Start...')
        update_example(node=l2, method='funderupdate', params={})
        update_example(node=l2, method='funderupdate', params={'policy': 'fixed', 'policy_mod': '50000sat', 'min_their_funding_msat': 1000, 'per_channel_min_msat': '1000sat', 'per_channel_max_msat': '500000sat', 'fund_probability': 100, 'fuzz_percent': 0, 'leases_only': False})
        inspect_res1 = update_example(node=l2, method='bkpr-inspect', params={'account': c23_chan_id})
        update_example(node=l2, method='bkpr-dumpincomecsv', params=['koinly', 'koinly.csv'])
        update_example(node=l2, method='bkpr-channelsapy', params={})
        bkprlistbal_res1 = update_example(node=l3, method='bkpr-listbalances', params={})
        update_example(node=l3, method='bkpr-listaccountevents', params={})
        update_example(node=l3, method='bkpr-listaccountevents', params=[c23_chan_id])
        update_example(node=l3, method='bkpr-listincome', params={})
        update_example(node=l3, method='bkpr-listincome', params={'consolidate_fees': False})
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['balance_msat'], 'original_value': bkprlistbal_res1['accounts'][0]['balances'][0]['balance_msat'], 'new_value': NEW_VALUES_LIST['balance_msat_1'] },
        ])
        logger.info('Bookkeeper Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating bookkeeper examples: {e}')


def generate_askrene_examples(l1, l2, l3, c12, c23):
    """Generates askrene examples"""
    try:
        logger.info('Askrene Start...')
        update_example(node=l2, method='askrene-disable-node', params={'layer': 'test_layer', 'node': l1.info['id']})
        update_example(node=l2, method='askrene-create-channel',
                       params={'layer': 'test_layers', 'source': l3.info['id'], 'destination': l1.info['id'], 'short_channel_id': c12, 'capacity_msat': '1000000sat', 'htlc_min': 100, 'htlc_max': '900000sat', 'base_fee': 1, 'proportional_fee': 2, 'delay': 18})
        update_example(node=l2, method='askrene-listlayers', params={})
        arinformchan_res1 = update_example(node=l2, method='askrene-inform-channel', params={'layer': 'test_layer', 'short_channel_id': c23, 'direction': 1, 'maximum_msat': 100000})
        listlayers_res2 = update_example(node=l2, method='askrene-listlayers', params={'layer': 'test_layer'})
        ts1 = only_one(only_one(listlayers_res2['layers'])['constraints'])['timestamp']
        time.sleep(2)
        arinformchan_res2 = update_example(node=l2, method='askrene-inform-channel', params=['test_layer', c12, 0, 12341234])
        update_example(node=l2, method='askrene-age', params={'layer': 'test_layer', 'cutoff': ts1})
        update_example(node=l2, method='askrene-age', params=['test_layer', ts1 + 1])
        update_example(node=l2, method='askrene-reserve', params={'path': [{'short_channel_id': c23, 'direction': 1, 'amount_msat': 1000000}]})
        update_example(node=l2, method='askrene-unreserve', params={'path': [{'short_channel_id': c23, 'direction': 1, 'amount_msat': 1000000}]})
        _, nodemap = generate_gossip_store([GenChannel(0, 1, forward=GenChannel.Half(propfee=10000)),
                                            GenChannel(0, 2, capacity_sats=9000),
                                            GenChannel(1, 3, forward=GenChannel.Half(propfee=20000)),
                                            GenChannel(0, 2, capacity_sats=10000),
                                            GenChannel(2, 4, forward=GenChannel.Half(delay=2000))])
        update_example(node=l1, method='getroutes',
                       params={'source': nodemap[0], 'destination': nodemap[2], 'amount_msat': 1000000, 'layers': [], 'maxfee_msat': 5000, 'finalcltv': 99})
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['cutoff'], 'original_value': ts1, 'new_value': NEW_VALUES_LIST['time_at_800'] },
            { 'data_keys': ['cutoff'], 'original_value': ts1 + 1, 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['timestamp'], 'original_value': arinformchan_res1['constraint']['timestamp'], 'new_value': NEW_VALUES_LIST['time_at_800'] },
            { 'data_keys': ['timestamp'], 'original_value': arinformchan_res2['constraint']['timestamp'], 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['timestamp'], 'original_value': listlayers_res2['layers'][0]['constraints'][0]['timestamp'], 'new_value': NEW_VALUES_LIST['time_at_800'] },
        ])
        logger.info('Askrene Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating askrene examples: {e}')


def generate_offers_renepay_examples(l1, l2, inv_l21, inv_l34):
    """Covers all offers and renepay related examples"""
    try:
        logger.info('Offers and Renepay Start...')

        # Offers & Offers Lists
        offer_l21 = update_example(node=l2, method='offer', params={'amount': '10000msat', 'description': 'Fish sale!'})
        offer_l22 = update_example(node=l2, method='offer', params={'amount': '1000sat', 'description': 'Coffee', 'quantity_max': 10})
        offer_l23 = l2.rpc.offer('2000sat', 'Offer to Disable')
        fetchinv_res1 = update_example(node=l1, method='fetchinvoice', params={'offer': offer_l21['bolt12'], 'payer_note': 'Thanks for the fish!'})
        fetchinv_res2 = update_example(node=l1, method='fetchinvoice', params={'offer': offer_l22['bolt12'], 'amount_msat': 2000000, 'quantity': 2})
        update_example(node=l2, method='disableoffer', params={'offer_id': offer_l23['offer_id']})
        update_example(node=l2, method='enableoffer', params={'offer_id': offer_l23['offer_id']})

        # Invoice Requests
        inv_req_l1_l22 = update_example(node=l2, method='invoicerequest', params={'amount': '10000sat', 'description': 'Requesting for invoice', 'issuer': 'clightning store'})
        disableinv_res1 = update_example(node=l2, method='disableinvoicerequest', params={'invreq_id': inv_req_l1_l22['invreq_id']})

        # Renepay
        renepay_res1 = update_example(node=l1, method='renepay', params={'invstring': inv_l21['bolt11'], 'amount_msat': 400000})
        renepay_res2 = update_example(node=l2, method='renepay', params={'invstring': inv_l34['bolt11']})
        renepaystatus_res1 = update_example(node=l1, method='renepaystatus', params={'invstring': inv_l21['bolt11']})
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['offer_id'], 'original_value': offer_l21['offer_id'], 'new_value': NEW_VALUES_LIST['offerid_l21'] },
            { 'data_keys': ['any', 'bolt12', 'invreq'], 'original_value': offer_l21['bolt12'], 'new_value': NEW_VALUES_LIST['bolt12_l21'] },
            { 'data_keys': ['offer_id'], 'original_value': offer_l22['offer_id'], 'new_value': NEW_VALUES_LIST['offerid_l22'] },
            { 'data_keys': ['any', 'bolt12', 'invreq'], 'original_value': offer_l22['bolt12'], 'new_value': NEW_VALUES_LIST['bolt12_l22'] },
            { 'data_keys': ['offer_id'], 'original_value': offer_l23['offer_id'], 'new_value': NEW_VALUES_LIST['offerid_l23'] },
            { 'data_keys': ['any', 'bolt12', 'invreq'], 'original_value': offer_l23['bolt12'], 'new_value': NEW_VALUES_LIST['bolt12_l23'] },
            { 'data_keys': ['invreq_id'], 'original_value': inv_req_l1_l22['invreq_id'], 'new_value': NEW_VALUES_LIST['invreq_id_2'] },
            { 'data_keys': ['any', 'bolt12', 'invreq'], 'original_value': disableinv_res1['bolt12'], 'new_value': NEW_VALUES_LIST['bolt12_l24'] },
            { 'data_keys': ['invoice'], 'original_value': fetchinv_res1['invoice'], 'new_value': NEW_VALUES_LIST['invoice_1'] },
            { 'data_keys': ['invoice'], 'original_value': fetchinv_res2['invoice'], 'new_value': NEW_VALUES_LIST['invoice_2'] },
            { 'data_keys': ['created_at'], 'original_value': renepay_res1['created_at'], 'new_value': NEW_VALUES_LIST['time_at_800'] },
            { 'data_keys': ['payment_preimage'], 'original_value': renepay_res1['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_r_1'] },
            { 'data_keys': ['created_at'], 'original_value': renepay_res2['created_at'], 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['payment_preimage'], 'original_value': renepay_res2['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_r_2'] },
        ])
        logger.info('Offers and Renepay Done!')
        return offer_l23, inv_req_l1_l22
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating offers or renepay examples: {e}')


def generate_wait_examples(l1, l2, bitcoind, executor):
    """Generates wait examples"""
    try:
        logger.info('Wait Start...')
        inv1 = l2.rpc.invoice(1000, 'inv1', 'inv1')
        inv2 = l2.rpc.invoice(2000, 'inv2', 'inv2')
        inv3 = l2.rpc.invoice(3000, 'inv3', 'inv3')
        inv4 = l2.rpc.invoice(4000, 'inv4', 'inv4')
        inv5 = l2.rpc.invoice(5000, 'inv5', 'inv5')
        # Wait invoice
        wi3 = executor.submit(l2.rpc.waitinvoice, 'inv3')
        time.sleep(1)
        l1.rpc.pay(inv2['bolt11'])
        time.sleep(1)
        wi2res = executor.submit(l2.rpc.waitinvoice, 'inv2').result(timeout=5)
        update_example(node=l2, method='waitinvoice', params={'label': 'inv2'}, res=wi2res, execute=False)

        l1.rpc.pay(inv3['bolt11'])
        wi3res = wi3.result(timeout=5)
        update_example(node=l2, method='waitinvoice', params=['inv3'], res=wi3res, execute=False)

        # Wait any invoice
        wai = executor.submit(l2.rpc.waitanyinvoice)
        time.sleep(1)
        l1.rpc.pay(inv5['bolt11'])
        l1.rpc.pay(inv4['bolt11'])
        waires = wai.result(timeout=5)
        update_example(node=l2, method='waitanyinvoice', params={}, res=waires, execute=False)
        pay_index = waires['pay_index']
        wai_pay_index_res = executor.submit(l2.rpc.waitanyinvoice, pay_index, 0).result(timeout=5)
        update_example(node=l2, method='waitanyinvoice', params={'lastpay_index': pay_index, 'timeout': 0}, res=wai_pay_index_res, execute=False)

        # Wait with subsystem examples
        update_example(node=l2, method='wait', params={'subsystem': 'invoices', 'indexname': 'created', 'nextvalue': 0})

        wspres_l1 = l1.rpc.wait(subsystem='sendpays', indexname='created', nextvalue=0)
        nextvalue = int(wspres_l1['created']) + 1
        wsp_created_l1 = executor.submit(l1.rpc.call, 'wait', {'subsystem': 'sendpays', 'indexname': 'created', 'nextvalue': nextvalue})
        wsp_updated_l1 = executor.submit(l1.rpc.call, 'wait', {'subsystem': 'sendpays', 'indexname': 'updated', 'nextvalue': nextvalue})
        time.sleep(1)
        routestep = {
            'amount_msat': 1000,
            'id': l2.info['id'],
            'delay': 5,
            'channel': first_scid(l1, l2)
        }
        l1.rpc.sendpay([routestep], inv1['payment_hash'], payment_secret=inv1['payment_secret'])
        wspc_res = wsp_created_l1.result(5)
        wspu_res = wsp_updated_l1.result(5)
        update_example(node=l1, method='wait', params={'subsystem': 'sendpays', 'indexname': 'created', 'nextvalue': nextvalue}, res=wspc_res, execute=False)
        update_example(node=l1, method='wait', params=['sendpays', 'updated', nextvalue], res=wspu_res, execute=False)

        # Wait blockheight
        curr_blockheight = l2.rpc.getinfo()['blockheight']
        update_example(node=l2, method='waitblockheight', params={'blockheight': curr_blockheight - 1, 'timeout': 600})
        wait_time = 60
        wbh = executor.submit(l2.rpc.waitblockheight, curr_blockheight + 1, wait_time)
        bitcoind.generate_block(1)
        sync_blockheight(bitcoind, [l2])
        wbhres = wbh.result(5)
        update_example(node=l2, method='waitblockheight', params={'blockheight': curr_blockheight + 1}, res=wbhres, execute=False)
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['payment_hash'], 'original_value': wspc_res['details']['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_wspc_1'] },
            { 'data_keys': ['payment_hash'], 'original_value': wspu_res['details']['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_wsup_2'] },
            { 'data_keys': ['paid_at'], 'original_value': waires['paid_at'], 'new_value': NEW_VALUES_LIST['time_at_800'] },
            { 'data_keys': ['expires_at'], 'original_value': waires['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_850'] },
            { 'data_keys': ['paid_at'], 'original_value': wai_pay_index_res['paid_at'], 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['expires_at'], 'original_value': wai_pay_index_res['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_860'] },
            { 'data_keys': ['bolt11'], 'original_value': wi2res['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_wt_1'] },
            { 'data_keys': ['payment_hash'], 'original_value': wi2res['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_winv_1'] },
            { 'data_keys': ['payment_preimage'], 'original_value': wi2res['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_wi_1'] },
            { 'data_keys': ['paid_at'], 'original_value': wi2res['paid_at'], 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['expires_at'], 'original_value': wi2res['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_860'] },
            { 'data_keys': ['bolt11'], 'original_value': wi3res['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_wt_2'] },
            { 'data_keys': ['payment_hash'], 'original_value': wi3res['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_winv_2'] },
            { 'data_keys': ['payment_preimage'], 'original_value': wi3res['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_wi_2'] },
            { 'data_keys': ['paid_at'], 'original_value': wi3res['paid_at'], 'new_value': NEW_VALUES_LIST['time_at_850'] },
            { 'data_keys': ['expires_at'], 'original_value': wi3res['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_870'] },
            { 'data_keys': ['blockheight'], 'original_value': wbhres['blockheight'], 'new_value': NEW_VALUES_LIST['blockheight_130'] },
        ])
        logger.info('Wait Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating wait examples: {e}')


def generate_utils_examples(l1, l2, l3, l4, l5, l6, c23, c34, inv_l11, inv_l22, rune_l21, bitcoind):
    """Generates other utilities examples"""
    try:
        logger.info('General Utils Start...')
        global CWD, FUND_CHANNEL_AMOUNT_SAT
        update_example(node=l2, method='batching', params={'enable': True})
        update_example(node=l2, method='ping', params={'id': l1.info['id'], 'len': 128, 'pongbytes': 128})
        update_example(node=l2, method='ping', params={'id': l3.info['id'], 'len': 1000, 'pongbytes': 65535})
        update_example(node=l2, method='help', params={'command': 'pay'})
        update_example(node=l2, method='help', params={'command': 'dev'})
        update_example(node=l2, method='setconfig', params=['autoclean-expiredinvoices-age', 300])
        update_example(node=l2, method='setconfig', params={'config': 'min-capacity-sat', 'val': 500000})
        update_example(node=l2, method='addgossip', params={'message': '010078c3314666731e339c0b8434f7824797a084ed7ca3655991a672da068e2c44cb53b57b53a296c133bc879109a8931dc31e6913a4bda3d58559b99b95663e6d52775579447ef5526300e1bb89bc6af8557aa1c3810a91814eafad6d103f43182e17b16644cb38c1d58a8edd094303959a9f1f9d42ff6c32a21f9c118531f512c8679cabaccc6e39dbd95a4dac90e75a258893c3aa3f733d1b8890174d5ddea8003cadffe557773c54d2c07ca1d535c4bf85885f879ae466c16a516e8ffcfec1740e3f5c98ca9ce13f452e867befef5517f306ed6aa5119b79059bcc6f68f329986b665d16de7bc7df64e3537504c91eeabe0e59d3a2b68e4216ead2b0f6e3ef7c000006226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f0000670000010000022d223620a359a47ff7f7ac447c85c46c923da53389221a0054c11c1e3ca31d590266e4598d1d3c415f572a8488830b60f7e744ed9235eb0b1ba93283b315c0351802e3bd38009866c9da8ec4aa99cc4ea9c6c0dd46df15c61ef0ce1f271291714e5702324266de8403b3ab157a09f1f784d587af61831c998c151bcc21bb74c2b2314b'})
        update_example(node=l2, method='addgossip', params={'message': '0102420526c8eb62ec6999bbee5f1de4841cab734374ec642b7deeb0259e76220bf82e97a241c907d5ff52019655f7f9a614c285bb35690f3a1a2b928d7b2349a79e06226e46111a0b59caaf126043eb5bbf28c34f3a5e332a1fc7b2b73cf188910f000067000001000065b32a0e010100060000000000000000000000010000000a000000003b023380'})
        update_example(node=l2, method='deprecations', params={'enable': True})
        update_example(node=l2, method='deprecations', params={'enable': False})
        getlog_res1 = update_example(node=l2, method='getlog', params={'level': 'unusual'})
        update_example(node=l2, method='notifications', params={'enable': True})
        update_example(node=l2, method='notifications', params={'enable': False})
        update_example(node=l2, method='check', params={'command_to_check': 'sendpay', 'route': [{'amount_msat': 1011, 'id': l3.info['id'], 'delay': 20, 'channel': c23}, {'amount_msat': 1000, 'id': l4.info['id'], 'delay': 10, 'channel': c34}], 'payment_hash': '0000000000000000000000000000000000000000000000000000000000000000'})
        update_example(node=l2, method='check', params={'command_to_check': 'dev', 'subcommand': 'slowcmd', 'msec': 1000})
        update_example(node=l6, method='check', params={'command_to_check': 'recover', 'hsmsecret': '6c696768746e696e672d31000000000000000000000000000000000000000000'})
        update_example(node=l2, method='plugin', params={'subcommand': 'start', 'plugin': os.path.join(CWD, 'tests/plugins/allow_even_msgs.py')})
        update_example(node=l2, method='plugin', params={'subcommand': 'stop', 'plugin': os.path.join(CWD, 'tests/plugins/allow_even_msgs.py')})
        update_example(node=l2, method='plugin', params=['list'])
        update_example(node=l2, method='sendcustommsg', params={'node_id': l3.info['id'], 'msg': '77770012'})

        # Wallet Utils
        address_l21 = update_example(node=l2, method='newaddr', params={})
        address_l22 = update_example(node=l2, method='newaddr', params={'addresstype': 'p2tr'})
        withdraw_l21 = update_example(node=l2, method='withdraw', params={'destination': address_l21['bech32'], 'satoshi': 555555})

        bitcoind.generate_block(4, wait_for_mempool=[withdraw_l21['txid']])
        sync_blockheight(bitcoind, [l2])

        funds_l2 = l2.rpc.listfunds()
        utxos = [f"{funds_l2['outputs'][2]['txid']}:{funds_l2['outputs'][2]['output']}"]
        example_utxos = ['utxo'+ ('02' * 30) + ':1']
        withdraw_l22 = update_example(node=l2, method='withdraw', params={'destination': address_l22['p2tr'], 'satoshi': 'all', 'feerate': '20000perkb', 'minconf': 0, 'utxos': utxos})
        bitcoind.generate_block(4, wait_for_mempool=[withdraw_l22['txid']])
        multiwithdraw_res1 = update_example(node=l2, method='multiwithdraw', params={'outputs': [{l1.rpc.newaddr()['bech32']: '2222000msat'}, {l1.rpc.newaddr()['bech32']: '3333000msat'}]})
        multiwithdraw_res2 = update_example(node=l2, method='multiwithdraw', params={'outputs': [{l1.rpc.newaddr('p2tr')['p2tr']: 1000}, {l1.rpc.newaddr()['bech32']: 1000}, {l2.rpc.newaddr()['bech32']: 1000}, {l3.rpc.newaddr()['bech32']: 1000}, {l3.rpc.newaddr()['bech32']: 1000}, {l4.rpc.newaddr('p2tr')['p2tr']: 1000}, {l1.rpc.newaddr()['bech32']: 1000}]})
        l2.rpc.connect(l4.info['id'], 'localhost', l4.port)
        l2.rpc.connect(l5.info['id'], 'localhost', l5.port)
        update_example(node=l2, method='disconnect', params={'id': l4.info['id'], 'force': False})
        update_example(node=l2, method='disconnect', params={'id': l5.info['id'], 'force': True})
        update_example(node=l2, method='parsefeerate', params=['unilateral_close'])
        update_example(node=l2, method='parsefeerate', params=['9999perkw'])
        update_example(node=l2, method='parsefeerate', params=[10000])
        update_example(node=l2, method='parsefeerate', params=['urgent'])
        update_example(node=l2, method='feerates', params={'style': 'perkw'})
        update_example(node=l2, method='feerates', params={'style': 'perkb'})
        update_example(node=l2, method='signmessage', params={'message': 'this is a test!'})
        update_example(node=l2, method='signmessage', params={'message': 'message for you'})
        update_example(node=l2, method='checkmessage', params={'message': 'testcase to check new rpc error', 'zbase': 'd66bqz3qsku5fxtqsi37j11pci47ydxa95iusphutggz9ezaxt56neh77kxe5hyr41kwgkncgiu94p9ecxiexgpgsz8daoq4tw8kj8yx', 'pubkey': '03be3b0e9992153b1d5a6e1623670b6c3663f72ce6cf2e0dd39c0a373a7de5a3b7'})
        update_example(node=l2, method='checkmessage', params={'message': 'this is a test!', 'zbase': 'd6tqaeuonjhi98mmont9m4wag7gg4krg1f4txonug3h31e9h6p6k6nbwjondnj46dkyausobstnk7fhyy998bhgc1yr98dfmhb4k54d7'})
        decodepay_res1 = update_example(node=l2, method='decodepay', params={'bolt11': inv_l11['bolt11']})
        decode_res1 = update_example(node=l2, method='decode', params=[rune_l21['rune']])
        decode_res2 = update_example(node=l2, method='decode', params=[inv_l22['bolt11']])

        # PSBT
        amount1 = 1000000
        amount2 = 3333333
        psbtoutput_res1 = update_example(node=l1, method='addpsbtoutput', params={'satoshi': amount1, 'locktime': 111}, description=[f'Here is a command to make a PSBT with a {amount1:,} sat output that leads to the on-chain wallet:'])
        update_example(node=l1, method='setpsbtversion', params={'psbt': psbtoutput_res1['psbt'], 'version': 0})
        psbtoutput_res2 = l1.rpc.addpsbtoutput(amount2, psbtoutput_res1['psbt'])
        update_example(node=l1, method='addpsbtoutput', params=[amount2, psbtoutput_res2['psbt']], res=psbtoutput_res2, execute=False)
        dest = l1.rpc.newaddr('p2tr')['p2tr']
        psbtoutput_res3 = update_example(node=l1, method='addpsbtoutput', params={'satoshi': amount2, 'initialpsbt': psbtoutput_res2['psbt'], 'destination': dest})
        l1.rpc.addpsbtoutput(amount2, psbtoutput_res2['psbt'], None, dest)
        update_example(node=l1, method='setpsbtversion', params=[psbtoutput_res2['psbt'], 2])

        out_total = Millisatoshi(3000000 * 1000)
        funding = l1.rpc.fundpsbt(satoshi=out_total, feerate=7500, startweight=42)
        psbt = bitcoind.rpc.decodepsbt(funding['psbt'])
        saved_input = psbt['tx']['vin'][0]
        l1.rpc.unreserveinputs(funding['psbt'])
        psbt = bitcoind.rpc.createpsbt([{'txid': saved_input['txid'],
                                        'vout': saved_input['vout']}], [])
        out_1_ms = Millisatoshi(funding['excess_msat'])
        output_psbt = bitcoind.rpc.createpsbt([], [{'bcrt1qeyyk6sl5pr49ycpqyckvmttus5ttj25pd0zpvg': float((out_total + out_1_ms).to_btc())}])
        fullpsbt = bitcoind.rpc.joinpsbts([funding['psbt'], output_psbt])
        l1.rpc.reserveinputs(fullpsbt)
        signed_psbt = l1.rpc.signpsbt(fullpsbt)['signed_psbt']
        sendpsbt_res1 = update_example(node=l1, method='sendpsbt', params={'psbt': signed_psbt})

        # SQL
        update_example(node=l1, filename='sql-template', method='sql', params={'query': 'SELECT id FROM peers'}, description=['A simple peers selection query:'])
        update_example(node=l1, filename='sql-template', method='sql', params=[f'SELECT nodeid,last_timestamp FROM nodes WHERE last_timestamp>=1669578892'], description=["A statement containing `=` needs `-o` in shell:"])
        update_example(node=l1, filename='sql-template', method='sql', params=[f"SELECT nodeid FROM nodes WHERE nodeid != x'{l3.info['id']}'"], description=['If you want to get specific nodeid values from the nodes table:'])
        update_example(node=l1, filename='sql-template', method='sql', params=[f"SELECT nodeid FROM nodes WHERE nodeid IN (x'{l1.info['id']}', x'{l3.info['id']}')"], description=["If you want to compare a BLOB column, `x'hex'` or `X'hex'` are needed:"])
        update_example(node=l1, filename='sql-template', method='sql', params=['SELECT peer_id, short_channel_id, to_us_msat, total_msat, peerchannels_status.status FROM peerchannels INNER JOIN peerchannels_status ON peerchannels_status.row = peerchannels.rowid'], description=['Related tables are usually referenced by JOIN:'])
        update_example(node=l2, filename='sql-template', method='sql', params=['SELECT COUNT(*) FROM forwards'], description=["Simple function usage, in this case COUNT. Strings inside arrays need \", and ' to protect them from the shell:"])
        update_example(node=l1, filename='sql-template', method='sql', params=['SELECT * from peerchannels_features'])
        example_log = getlog_res1['log']
        for i, log_entry in enumerate(example_log):
            if 'num_skipped' in log_entry:
                log_entry['num_skipped'] = 144 + i
            if 'time' in log_entry:
                log_entry['time'] = f"{70.8 + i}00000000"
            if 'node_id' in log_entry:
                log_entry['node_id'] = 'nodeid' + ('01' * 30)
            if log_entry.get('log', '').startswith('No peer channel with'):
                log_entry['log'] = 'No peer channel with scid=228x1x1'
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['any', 'psbt', 'initialpsbt'], 'original_value': psbtoutput_res1['psbt'], 'new_value': NEW_VALUES_LIST['init_psbt_1'] },
            { 'data_keys': ['any', 'psbt', 'initialpsbt'], 'original_value': psbtoutput_res2['psbt'], 'new_value': NEW_VALUES_LIST['init_psbt_2'] },
            { 'data_keys': ['any', 'psbt', 'initialpsbt'], 'original_value': psbtoutput_res3['psbt'], 'new_value': NEW_VALUES_LIST['init_psbt_3'] },
            { 'data_keys': ['destination'], 'original_value': dest, 'new_value': NEW_VALUES_LIST['destination_1'] },
            { 'data_keys': ['created_at'], 'original_value': decode_res2['created_at'], 'new_value': NEW_VALUES_LIST['time_at_760'] },
            { 'data_keys': ['signature'], 'original_value': decode_res2['signature'], 'new_value': NEW_VALUES_LIST['signature_1'] },
            { 'data_keys': ['short_channel_id'], 'original_value': decode_res2['routes'][0][0]['short_channel_id'], 'new_value': NEW_VALUES_LIST['c23'] },
            { 'data_keys': ['created_at'], 'original_value': decodepay_res1['created_at'], 'new_value': NEW_VALUES_LIST['time_at_760'] },
            { 'data_keys': ['signature'], 'original_value': decodepay_res1['signature'], 'new_value': NEW_VALUES_LIST['signature_2'] },
            { 'data_keys': ['tx'], 'original_value': multiwithdraw_res1['tx'], 'new_value': NEW_VALUES_LIST['tx_55'] },
            { 'data_keys': ['txid'], 'original_value': multiwithdraw_res1['txid'], 'new_value': NEW_VALUES_LIST['txid_55'] },
            { 'data_keys': ['tx'], 'original_value': multiwithdraw_res2['tx'], 'new_value': NEW_VALUES_LIST['tx_56'] },
            { 'data_keys': ['txid'], 'original_value': multiwithdraw_res2['txid'], 'new_value': NEW_VALUES_LIST['txid_56'] },
            { 'data_keys': ['psbt'], 'original_value': signed_psbt, 'new_value': NEW_VALUES_LIST['psbt_1'] },
            { 'data_keys': ['tx'], 'original_value': sendpsbt_res1['tx'], 'new_value': NEW_VALUES_LIST['tx_61'] },
            { 'data_keys': ['txid'], 'original_value': sendpsbt_res1['txid'], 'new_value': NEW_VALUES_LIST['txid_61'] },
            
            { 'data_keys': ['destination'], 'original_value': address_l21['bech32'], 'new_value': NEW_VALUES_LIST['destination_2'] },
            { 'data_keys': ['destination'], 'original_value': address_l22['p2tr'], 'new_value': NEW_VALUES_LIST['destination_3'] },
            { 'data_keys': ['utxos'], 'original_value': utxos, 'new_value': example_utxos },
            { 'data_keys': ['tx'], 'original_value': withdraw_l21['tx'], 'new_value': NEW_VALUES_LIST['tx_91'] },
            { 'data_keys': ['txid'], 'original_value': withdraw_l21['txid'], 'new_value': NEW_VALUES_LIST['withdraw_txid_l21'] },
            { 'data_keys': ['psbt'], 'original_value': withdraw_l21['psbt'], 'new_value': NEW_VALUES_LIST['psbt_7'] },
            { 'data_keys': ['tx'], 'original_value': withdraw_l22['tx'], 'new_value': NEW_VALUES_LIST['tx_92'] },
            { 'data_keys': ['txid'], 'original_value': withdraw_l22['txid'], 'new_value': NEW_VALUES_LIST['withdraw_txid_l22'] },
            { 'data_keys': ['psbt'], 'original_value': withdraw_l22['psbt'], 'new_value': NEW_VALUES_LIST['psbt_8'] },

            { 'data_keys': ['created_at'], 'original_value': getlog_res1['created_at'], 'new_value': NEW_VALUES_LIST['time_at_710'] },
            { 'data_keys': ['bytes_used'], 'original_value': getlog_res1['bytes_used'], 'new_value': NEW_VALUES_LIST['bytes_used'] },
            { 'data_keys': ['bytes_max'], 'original_value': getlog_res1['bytes_max'], 'new_value': NEW_VALUES_LIST['bytes_max'] },
            { 'data_keys': ['log'], 'original_value': getlog_res1['log'], 'new_value': example_log },
        ])
        logger.info('General Utils Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating utils examples: {e}')


def generate_splice_examples(node_factory, bitcoind):
    """Generates splice related examples"""
    try:
        logger.info('Splice Start...')
        global FUND_WALLET_AMOUNT_SAT, FUND_CHANNEL_AMOUNT_SAT
        # Basic setup for l7->l8
        options = [
            {
                'experimental-splicing': None,
                'allow-deprecated-apis': True,
                'allow_bad_gossip': True,
                'broken_log': '.*',
                'dev-bitcoind-poll': 3,
            }.copy()
            for i in range(2)
        ]
        l7, l8 = node_factory.get_nodes(2, opts=options)
        l7.fundwallet(FUND_WALLET_AMOUNT_SAT)
        l7.rpc.connect(l8.info['id'], 'localhost', l8.port)
        c78, c78res = l7.fundchannel(l8, FUND_CHANNEL_AMOUNT_SAT)
        mine_funding_to_announce(bitcoind, [l7, l8])
        l7.wait_channel_active(c78)
        chan_id_78 = l7.get_channel_id(l8)
        # Splice
        funds_result_1 = l7.rpc.fundpsbt('109000sat', 'slow', 166, excess_as_change=True)
        spinit_res1 = update_example(node=l7, method='splice_init', params={'channel_id': chan_id_78, 'relative_amount': 100000, 'initialpsbt': funds_result_1['psbt']})
        spupdate_res1 = update_example(node=l7, method='splice_update', params={'channel_id': chan_id_78, 'psbt': spinit_res1['psbt']})
        signpsbt_res1 = l7.rpc.signpsbt(spupdate_res1['psbt'])
        spsigned_res1 = update_example(node=l7, method='splice_signed', params={'channel_id': chan_id_78, 'psbt': signpsbt_res1['signed_psbt']})

        bitcoind.generate_block(1)
        sync_blockheight(bitcoind, [l7])
        l7.daemon.wait_for_log(' to CHANNELD_NORMAL')
        time.sleep(1)

        # Splice out
        funds_result_2 = l7.rpc.addpsbtoutput(100000)

        # Pay with fee by subtracting 5000 from channel balance
        spinit_res2 = update_example(node=l7, method='splice_init', params=[chan_id_78, -105000, funds_result_2['psbt']])
        spupdate_res2 = update_example(node=l7, method='splice_update', params=[chan_id_78, spinit_res2['psbt']])
        spsigned_res2 = update_example(node=l7, method='splice_signed', params=[chan_id_78, spupdate_res2['psbt']])
        update_example(node=l7, method='stop', params={})
        
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l7.info['id'], 'new_value': NEW_VALUES_LIST['l7_id'] },
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l8.info['id'], 'new_value': NEW_VALUES_LIST['l8_id'] },

            { 'data_keys': ['alias'], 'original_value': l7.info['alias'], 'new_value': NEW_VALUES_LIST['l7_alias'] },
            { 'data_keys': ['port'], 'original_value': l7.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l7_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l7.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l7_addr'] },
            { 'data_keys': ['alias'], 'original_value': l8.info['alias'], 'new_value': NEW_VALUES_LIST['l8_alias'] },
            { 'data_keys': ['port'], 'original_value': l8.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l8_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l8.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l8_addr'] },

            { 'data_keys': ['scid', 'channel'], 'original_value': c78, 'new_value': NEW_VALUES_LIST['c78'] },
            { 'data_keys': ['tx'], 'original_value': c78res['tx'], 'new_value': NEW_VALUES_LIST['c78_tx'] },
            { 'data_keys': ['txid'], 'original_value': c78res['txid'], 'new_value': NEW_VALUES_LIST['c78_txid'] },
            { 'data_keys': ['any', 'channel_id', 'account'], 'original_value': chan_id_78, 'new_value': NEW_VALUES_LIST['c78_channel_id'] },

            { 'data_keys': ['any', 'psbt'], 'original_value': spinit_res1['psbt'], 'new_value': NEW_VALUES_LIST['psbt_1'] },
            { 'data_keys': ['any', 'psbt'], 'original_value': spinit_res2['psbt'], 'new_value': NEW_VALUES_LIST['psbt_2'] },
            { 'data_keys': ['any', 'initialpsbt', 'psbt'], 'original_value': funds_result_1['psbt'], 'new_value': NEW_VALUES_LIST['psbt_3'] },
            { 'data_keys': ['any', 'initialpsbt', 'psbt'], 'original_value': funds_result_2['psbt'], 'new_value': NEW_VALUES_LIST['psbt_4'] },
            { 'data_keys': ['psbt'], 'original_value': spupdate_res1['psbt'], 'new_value': NEW_VALUES_LIST['psbt_5'] },
            { 'data_keys': ['any', 'psbt'], 'original_value': spupdate_res2['psbt'], 'new_value': NEW_VALUES_LIST['psbt_6'] },
            { 'data_keys': ['tx'], 'original_value': spsigned_res1['tx'], 'new_value': NEW_VALUES_LIST['send_tx_1'] },
            { 'data_keys': ['txid'], 'original_value': spsigned_res1['txid'], 'new_value': NEW_VALUES_LIST['send_txid_1'] },
            { 'data_keys': ['tx'], 'original_value': spsigned_res2['tx'], 'new_value': NEW_VALUES_LIST['send_tx_2'] },
            { 'data_keys': ['txid'], 'original_value': spsigned_res2['txid'], 'new_value': NEW_VALUES_LIST['send_txid_2'] },
            { 'data_keys': ['psbt'], 'original_value': signpsbt_res1['signed_psbt'], 'new_value': NEW_VALUES_LIST['signed_psbt_1'] },
        ])
        logger.info('Splice Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating splicing examples: {e}')


def generate_channels_examples(node_factory, bitcoind, l1, l3, l4, l5):
    """Generates fundchannel and openchannel related examples"""
    try:
        logger.info('Channels Start...')
        global FUND_WALLET_AMOUNT_SAT, FUND_CHANNEL_AMOUNT_SAT
        # Basic setup for l9->l10 for fundchannel examples
        options = [
            {
                'may_reconnect': True,
                'dev-no-reconnect': None,
                'allow-deprecated-apis': True,
                'allow_bad_gossip': True,
                'broken_log': '.*',
                'dev-bitcoind-poll': 3,
            }.copy()
            for i in range(2)
        ]
        l9, l10 = node_factory.get_nodes(2, opts=options)
        amount = 2 ** 24
        l9.fundwallet(amount + 10000000)
        bitcoind.generate_block(1)
        wait_for(lambda: len(l9.rpc.listfunds()["outputs"]) != 0)
        l9.rpc.connect(l10.info['id'], 'localhost', l10.port)

        fund_start_res1 = update_example(node=l9, method='fundchannel_start', params=[l10.info['id'], amount])
        outputs_1 = [{fund_start_res1['funding_address']: amount}]
        example_outputs_1 = [{'bcrt1p00' + ('02' * 28): amount}]
        tx_prep_1 = update_example(node=l9, method='txprepare', params=[outputs_1])
        update_example(node=l9, method='fundchannel_cancel', params=[l10.info['id']])
        txdiscard_res1 = update_example(node=l9, method='txdiscard', params=[tx_prep_1['txid']])
        fund_start_res2 = update_example(node=l9, method='fundchannel_start', params={'id': l10.info['id'], 'amount': amount})
        outputs_2 = [{fund_start_res2['funding_address']: amount}]
        example_outputs_2 = [{'bcrt1p00' + ('03' * 28): amount}]
        tx_prep_2 = update_example(node=l9, method='txprepare', params={'outputs': outputs_2})
        fcc_res1 = update_example(node=l9, method='fundchannel_complete', params=[l10.info['id'], tx_prep_2['psbt']])
        txsend_res1 = update_example(node=l9, method='txsend', params=[tx_prep_2['txid']])
        l9.rpc.close(l10.info['id'])

        bitcoind.generate_block(1)
        sync_blockheight(bitcoind, [l9])

        amount = 1000000
        fund_start_res3 = l9.rpc.fundchannel_start(l10.info['id'], amount)
        tx_prep_3 = l9.rpc.txprepare([{fund_start_res3['funding_address']: amount}])
        update_example(node=l9, method='fundchannel_cancel', params={'id': l10.info['id']})
        txdiscard_res2 = update_example(node=l9, method='txdiscard', params={'txid': tx_prep_3['txid']})
        funding_addr = l9.rpc.fundchannel_start(l10.info['id'], amount)['funding_address']
        tx_prep_4 = l9.rpc.txprepare([{funding_addr: amount}])
        fcc_res2 = update_example(node=l9, method='fundchannel_complete', params={'id': l10.info['id'], 'psbt': tx_prep_4['psbt']})
        txsend_res2 = update_example(node=l9, method='txsend', params={'txid': tx_prep_4['txid']})
        l9.rpc.close(l10.info['id'])

        # Basic setup for l11->l12 for openchannel examples
        options = [
            {
                'experimental-dual-fund': None,
                'may_reconnect': True,
                'dev-no-reconnect': None,
                'allow_warning': True,
                'allow-deprecated-apis': True,
                'allow_bad_gossip': True,
                'broken_log': '.*',
                'dev-bitcoind-poll': 3,
            }.copy()
            for i in range(2)
        ]
        l11, l12 = node_factory.get_nodes(2, opts=options)
        l11.fundwallet(FUND_WALLET_AMOUNT_SAT)
        l11.rpc.connect(l12.info['id'], 'localhost', l12.port)
        c1112res = l11.rpc.fundchannel(l12.info['id'], FUND_CHANNEL_AMOUNT_SAT)
        chan_id = c1112res['channel_id']
        vins = bitcoind.rpc.decoderawtransaction(c1112res['tx'])['vin']
        assert(only_one(vins))
        prev_utxos = ["{}:{}".format(vins[0]['txid'], vins[0]['vout'])]
        example_utxos = ['utxo' + ('01' * 30) + ':1']

        l11.daemon.wait_for_log(' to DUALOPEND_AWAITING_LOCKIN')
        chan = only_one(l11.rpc.listpeerchannels(l12.info['id'])['channels'])
        rate = int(chan['feerate']['perkw'])
        next_feerate = '{}perkw'.format(rate * 4)

        # Initiate an RBF
        startweight = 42 + 172
        initpsbt_1 = update_example(node=l11, method='utxopsbt', params=[FUND_CHANNEL_AMOUNT_SAT, next_feerate, startweight, prev_utxos, None, True, None, None, True])
        openchannelbump_res1 = update_example(node=l11, method='openchannel_bump', params=[chan_id, FUND_CHANNEL_AMOUNT_SAT, initpsbt_1['psbt'], next_feerate])

        update_example(node=l11, method='openchannel_abort', params={'channel_id': chan_id})
        openchannelbump_res2 = update_example(node=l11, method='openchannel_bump', params={'channel_id': chan_id, 'amount': FUND_CHANNEL_AMOUNT_SAT, 'initialpsbt': initpsbt_1['psbt'], 'funding_feerate': next_feerate})
        openchannelupdate_res1 = update_example(node=l11, method='openchannel_update', params={'channel_id': chan_id, 'psbt': openchannelbump_res2['psbt']})
        signed_psbt_1 = update_example(node=l11, method='signpsbt', params={'psbt': openchannelupdate_res1['psbt']})
        openchannelsigned_res1 = update_example(node=l11, method='openchannel_signed', params={'channel_id': chan_id, 'signed_psbt': signed_psbt_1['signed_psbt']})

        # 5x the feerate to beat the min-relay fee
        chan = only_one(l11.rpc.listpeerchannels(l12.info['id'])['channels'])
        rate = int(chan['feerate']['perkw'])
        next_feerate = '{}perkw'.format(rate * 5)

        # Another RBF with double the channel amount
        startweight = 42 + 172
        initpsbt_2 = update_example(node=l11, method='utxopsbt', params={'satoshi': FUND_CHANNEL_AMOUNT_SAT * 2, 'feerate': next_feerate, 'startweight': startweight, 'utxos': prev_utxos, 'reservedok': True, 'excess_as_change': True})
        openchannelbump_res3 = update_example(node=l11, method='openchannel_bump', params=[chan_id, FUND_CHANNEL_AMOUNT_SAT * 2, initpsbt_2['psbt'], next_feerate])
        openchannelupdate_res2 = update_example(node=l11, method='openchannel_update', params=[chan_id, openchannelbump_res3['psbt']])
        signed_psbt_2 = update_example(node=l11, method='signpsbt', params=[openchannelupdate_res2['psbt']])
        openchannelsigned_res2 = update_example(node=l11, method='openchannel_signed', params=[chan_id, signed_psbt_2['signed_psbt']])

        bitcoind.generate_block(1)
        sync_blockheight(bitcoind, [l11])
        l11.daemon.wait_for_log(' to CHANNELD_NORMAL')

        # Fundpsbt, channelopen init, abort, unreserve
        psbt_init_res1 = update_example(node=l11, method='fundpsbt', params={'satoshi': FUND_CHANNEL_AMOUNT_SAT, 'feerate': '253perkw', 'startweight': 250, 'reserve': 0})
        openchannelinit_res1 = update_example(node=l11, method='openchannel_init', params={'id': l12.info['id'], 'amount': FUND_CHANNEL_AMOUNT_SAT, 'initialpsbt': psbt_init_res1['psbt']})
        l11.rpc.openchannel_abort(openchannelinit_res1['channel_id'])
        update_example(node=l11, method='unreserveinputs', params={'psbt': psbt_init_res1['psbt'], 'reserve': 200})

        psbt_init_res2 = update_example(node=l11, method='fundpsbt', params={'satoshi': FUND_CHANNEL_AMOUNT_SAT // 2, 'feerate': 'urgent', 'startweight': 166, 'reserve': 0, 'excess_as_change': True, 'min_witness_weight': 110})
        openchannelinit_res2 = update_example(node=l11, method='openchannel_init', params=[l12.info['id'], FUND_CHANNEL_AMOUNT_SAT // 2, psbt_init_res2['psbt']])
        l11.rpc.openchannel_abort(openchannelinit_res2['channel_id'])
        update_example(node=l11, method='unreserveinputs', params=[psbt_init_res2['psbt']])

        # Reserveinputs
        bitcoind.generate_block(1)
        sync_blockheight(bitcoind, [l11])
        outputs = l11.rpc.listfunds()['outputs']
        psbt_1 = bitcoind.rpc.createpsbt([{'txid': outputs[0]['txid'], 'vout': outputs[0]['output']}], [])
        reserveinputs_res1 = update_example(node=l11, method='reserveinputs', params={'psbt': psbt_1})
        l11.rpc.unreserveinputs(psbt_1)
        psbt_2 = bitcoind.rpc.createpsbt([{'txid': outputs[1]['txid'], 'vout': outputs[1]['output']}], [])
        reserveinputs_res2 = update_example(node=l11, method='reserveinputs', params={'psbt': psbt_2})
        l11.rpc.unreserveinputs(psbt_2)

        # Multifundchannel 1
        l3.rpc.connect(l5.info['id'], 'localhost', l5.port)
        l4.rpc.connect(l1.info['id'], 'localhost', l1.port)
        c35res = update_example(node=l3, method='fundchannel', params={'id': l5.info['id'], 'amount': FUND_CHANNEL_AMOUNT_SAT, 'announce': True})
        outputs = l4.rpc.listfunds()['outputs']
        utxo = f"{outputs[0]['txid']}:{outputs[0]['output']}"
        c41res = update_example(node=l4, method='fundchannel',
                                params={'id': l1.info['id'], 'amount': 'all', 'feerate': 'normal', 'push_msat': 100000, 'utxos': [utxo]},
                                description=[f'This example shows how to to open new channel with peer 1 from one whole utxo (you can use **listfunds** command to get txid and vout):'])
        # Close newly funded channels to bring the setup back to initial state
        l3.rpc.close(c35res['channel_id'])
        l4.rpc.close(c41res['channel_id'])
        l3.rpc.disconnect(l5.info['id'], True)
        l4.rpc.disconnect(l1.info['id'], True)

        # Multifundchannel 2
        l1.fundwallet(10**8)
        l1.rpc.connect(l3.info['id'], 'localhost', l3.port)
        l1.rpc.connect(l4.info['id'], 'localhost', l4.port)
        l1.rpc.connect(l5.info['id'], 'localhost', l5.port)
        destinations_1 = [
            {
                'id': f'{l3.info["id"]}@127.0.0.1:{l3.port}',
                'amount': '20000sat'
            },
            {
                'id': f'{l4.info["id"]}@127.0.0.1:{l4.port}',
                'amount': '0.0003btc'
            },
            {
                'id': f'{l5.info["id"]}@127.0.0.1:{l5.port}',
                'amount': 'all'
            }
        ]
        example_destinations_1 = [
            {
                'id': 'nodeid' + ('03' * 30) + '@127.0.0.1:19736',
                'amount': '20000sat'
            },
            {
                'id': 'nodeid' + ('04' * 30) + '@127.0.0.1:19737',
                'amount': '0.0003btc'
            },
            {
                'id': 'nodeid' + ('05' * 30) + '@127.0.0.1:19738',
                'amount': 'all'
            }
        ]
        multifund_res1 = update_example(node=l1, method='multifundchannel', params={
            'destinations': destinations_1,
            'feerate': '10000perkw',
            'commitment_feerate': '2000perkw'
        }, description=[
            'This example opens three channels at once, with amounts 20,000 sats, 30,000 sats',
            'and the final channel using all remaining funds (actually, capped at 16,777,215 sats',
            'because large-channels is not enabled):'
        ])
        for channel in multifund_res1['channel_ids']:
            l1.rpc.close(channel['channel_id'])
        l1.fundwallet(10**8)
        
        destinations_2 = [
            {
                'id': f'03a389b3a2f7aa6f9f4ccc19f2bd7a2eba83596699e86b715caaaa147fc37f3144@127.0.0.1:{l3.port}',
                'amount': 50000
            },
            {
                'id': f'{l4.info["id"]}@127.0.0.1:{l4.port}',
                'amount': 50000
            },
            {
                'id': f'{l1.info["id"]}@127.0.0.1:{l1.port}',
                'amount': 50000
            }
        ]
        example_destinations_2 = [
            {
                'id': f'fakenodeid' + ('03' * 28) + '@127.0.0.1:19736',
                'amount': 50000
            },
            {
                'id': 'nodeid' + ('04' * 30) + '@127.0.0.1:19737',
                'amount': 50000
            },
            {
                'id': 'nodeid' + ('01' * 30) + '@127.0.0.1:19734',
                'amount': 50000
            }            
        ]
        multifund_res2 = update_example(node=l1, method='multifundchannel', params={'destinations': destinations_2, 'minchannels': 1})
        # Close newly funded channels to bring the setup back to initial state
        for channel in multifund_res2['channel_ids']:
            l1.rpc.close(channel['channel_id'])
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l9.info['id'], 'new_value': NEW_VALUES_LIST['l9_id'] },
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l10.info['id'], 'new_value': NEW_VALUES_LIST['l10_id'] },
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l11.info['id'], 'new_value': NEW_VALUES_LIST['l11_id'] },
            { 'data_keys': ['any', 'id', 'pubkey', 'destination'], 'original_value': l12.info['id'], 'new_value': NEW_VALUES_LIST['l12_id'] },

            { 'data_keys': ['alias'], 'original_value': l9.info['alias'], 'new_value': NEW_VALUES_LIST['l9_alias'] },
            { 'data_keys': ['port'], 'original_value': l9.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l9_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l9.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l9_addr'] },
            { 'data_keys': ['alias'], 'original_value': l10.info['alias'], 'new_value': NEW_VALUES_LIST['l10_alias'] },
            { 'data_keys': ['port'], 'original_value': l10.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l10_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l10.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l10_addr'] },
            { 'data_keys': ['any', 'txid'], 'original_value': tx_prep_1['txid'], 'new_value': NEW_VALUES_LIST['txprep_txid_1'] },
            { 'data_keys': ['initialpsbt', 'psbt', 'signed_psbt'], 'original_value': tx_prep_1['psbt'], 'new_value': NEW_VALUES_LIST['psbt_9'] },
            { 'data_keys': ['unsigned_tx'], 'original_value': tx_prep_2['unsigned_tx'], 'new_value': NEW_VALUES_LIST['unsigned_tx_1'] },
            { 'data_keys': ['any', 'initialpsbt', 'psbt', 'signed_psbt'], 'original_value': tx_prep_2['psbt'], 'new_value': NEW_VALUES_LIST['psbt_10'] },
            { 'data_keys': ['any', 'txid'], 'original_value': tx_prep_2['txid'], 'new_value': NEW_VALUES_LIST['txprep_txid_2'] },
            { 'data_keys': ['any', 'txid'], 'original_value': tx_prep_3['txid'], 'new_value': NEW_VALUES_LIST['txprep_txid_3'] },
            { 'data_keys': ['initialpsbt', 'psbt', 'signed_psbt'], 'original_value': tx_prep_3['psbt'], 'new_value': NEW_VALUES_LIST['psbt_11'] },
            { 'data_keys': ['txid'], 'original_value': tx_prep_4['txid'], 'new_value': NEW_VALUES_LIST['txprep_txid_4'] },
            { 'data_keys': ['unsigned_tx'], 'original_value': tx_prep_4['unsigned_tx'], 'new_value': NEW_VALUES_LIST['unsigned_tx_2'] },
            { 'data_keys': ['initialpsbt', 'psbt', 'signed_psbt'], 'original_value': tx_prep_4['psbt'], 'new_value': NEW_VALUES_LIST['psbt_12'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': fcc_res1['channel_id'], 'new_value': NEW_VALUES_LIST['c910_channel_id_1'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': fcc_res2['channel_id'], 'new_value': NEW_VALUES_LIST['c910_channel_id_2'] },
            { 'data_keys': ['alias'], 'original_value': l11.info['alias'], 'new_value': NEW_VALUES_LIST['l11_alias'] },
            { 'data_keys': ['port'], 'original_value': l11.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l11_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l11.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l11_addr'] },
            { 'data_keys': ['alias'], 'original_value': l12.info['alias'], 'new_value': NEW_VALUES_LIST['l12_alias'] },
            { 'data_keys': ['port'], 'original_value': l12.info['binding'][0]['port'], 'new_value': NEW_VALUES_LIST['l12_port'] },
            { 'data_keys': ['addr'], 'original_value': f'127.0.0.1:{l12.info["binding"][0]["port"]}', 'new_value': NEW_VALUES_LIST['l12_addr'] },

            { 'data_keys': ['tx'], 'original_value': c1112res['tx'], 'new_value': NEW_VALUES_LIST['c1112_tx'] },
            { 'data_keys': ['txid'], 'original_value': c1112res['txid'], 'new_value': NEW_VALUES_LIST['c1112_txid'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': c1112res['channel_id'], 'new_value': NEW_VALUES_LIST['c1112_channel_id'] },
            { 'data_keys': ['tx'], 'original_value': c35res['tx'], 'new_value': NEW_VALUES_LIST['c35_tx'] },
            { 'data_keys': ['txid'], 'original_value': c35res['txid'], 'new_value': NEW_VALUES_LIST['c35_txid'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': c35res['channel_id'], 'new_value': NEW_VALUES_LIST['c35_channel_id'] },
            { 'data_keys': ['tx'], 'original_value': c41res['tx'], 'new_value': NEW_VALUES_LIST['c41_tx'] },
            { 'data_keys': ['txid'], 'original_value': c41res['txid'], 'new_value': NEW_VALUES_LIST['c41_txid'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': c41res['channel_id'], 'new_value': NEW_VALUES_LIST['c41_channel_id'] },
            { 'data_keys': ['destinations'], 'original_value': destinations_1, 'new_value': example_destinations_1 },
            { 'data_keys': ['channel_id', 'account'], 'original_value': multifund_res1['channel_ids'][0]['channel_id'], 'new_value': NEW_VALUES_LIST['mf_channel_id_1'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': multifund_res1['channel_ids'][1]['channel_id'], 'new_value': NEW_VALUES_LIST['mf_channel_id_2'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': multifund_res1['channel_ids'][2]['channel_id'], 'new_value': NEW_VALUES_LIST['mf_channel_id_3'] },
            { 'data_keys': ['tx'], 'original_value': multifund_res1['tx'], 'new_value': NEW_VALUES_LIST['multi_tx_1'] },
            { 'data_keys': ['txid'], 'original_value': multifund_res1['txid'], 'new_value': NEW_VALUES_LIST['multi_txid_1'] },
            { 'data_keys': ['destinations'], 'original_value': destinations_2, 'new_value': example_destinations_2 },

            { 'data_keys': ['channel_id', 'account'], 'original_value': multifund_res2['channel_ids'][0]['channel_id'], 'new_value': NEW_VALUES_LIST['mf_channel_id_4'] },
            { 'data_keys': ['tx'], 'original_value': multifund_res2['tx'], 'new_value': NEW_VALUES_LIST['multi_tx_2'] },
            { 'data_keys': ['txid'], 'original_value': multifund_res2['txid'], 'new_value': NEW_VALUES_LIST['multi_txid_2'] },
            { 'data_keys': ['message'], 'original_value': multifund_res2['failed'][0]['error']['message'], 'new_value': NEW_VALUES_LIST['error_message_1'] },
           
            { 'data_keys': ['utxos'], 'original_value': [utxo], 'new_value': [NEW_VALUES_LIST['c35_txid'] + ':1'] },
            { 'data_keys': ['any', 'funding_address'], 'original_value': fund_start_res1['funding_address'], 'new_value': NEW_VALUES_LIST['destination_4'] },
            { 'data_keys': ['any', 'outputs'], 'original_value': outputs_1, 'new_value':  example_outputs_1 },
            { 'data_keys': ['scriptpubkey'], 'original_value': fund_start_res1['scriptpubkey'], 'new_value': NEW_VALUES_LIST['script_pubkey_1'] },
            { 'data_keys': ['any', 'funding_address'], 'original_value': fund_start_res2['funding_address'], 'new_value': NEW_VALUES_LIST['destination_5'] },
            { 'data_keys': ['any', 'outputs'], 'original_value': outputs_2, 'new_value':  example_outputs_2 },
            { 'data_keys': ['scriptpubkey'], 'original_value': fund_start_res2['scriptpubkey'], 'new_value': NEW_VALUES_LIST['script_pubkey_2'] },

            { 'data_keys': ['initialpsbt', 'psbt'], 'original_value': psbt_init_res1['psbt'], 'new_value': NEW_VALUES_LIST['psbt_13'] },
            { 'data_keys': ['any', 'initialpsbt', 'psbt'], 'original_value': psbt_init_res2['psbt'], 'new_value': NEW_VALUES_LIST['psbt_14'] },

            { 'data_keys': ['any', 'txid'], 'original_value': initpsbt_1['reservations'][0]['txid'], 'new_value': NEW_VALUES_LIST['utxo_1'] },
            { 'data_keys': ['any', 'initialpsbt', 'psbt'], 'original_value': initpsbt_1['psbt'], 'new_value': NEW_VALUES_LIST['psbt_15'] },
            { 'data_keys': ['any', 'initialpsbt', 'psbt'], 'original_value': initpsbt_2['psbt'], 'new_value': NEW_VALUES_LIST['psbt_16'] },
            { 'data_keys': ['any', 'txid'], 'original_value': initpsbt_2['reservations'][0]['txid'], 'new_value': NEW_VALUES_LIST['utxo_1'] },

            { 'data_keys': ['initialpsbt', 'psbt', 'signed_psbt'], 'original_value': openchannelinit_res1['psbt'], 'new_value': NEW_VALUES_LIST['psbt_17'] },
            { 'data_keys': ['funding_serial'], 'original_value': openchannelinit_res1['funding_serial'], 'new_value': NEW_VALUES_LIST['funding_serial_1'] },
            { 'data_keys': ['initialpsbt', 'psbt', 'signed_psbt'], 'original_value': openchannelinit_res2['psbt'], 'new_value': NEW_VALUES_LIST['psbt_18'] },
            { 'data_keys': ['funding_serial'], 'original_value': openchannelinit_res2['funding_serial'], 'new_value': NEW_VALUES_LIST['funding_serial_2'] },

            { 'data_keys': ['initialpsbt', 'psbt', 'signed_psbt'], 'original_value': openchannelbump_res1['psbt'], 'new_value': NEW_VALUES_LIST['psbt_19'] },
            { 'data_keys': ['initialpsbt', 'psbt', 'signed_psbt'], 'original_value': openchannelbump_res2['psbt'], 'new_value': NEW_VALUES_LIST['psbt_20'] },
            { 'data_keys': ['any', 'initialpsbt', 'psbt', 'signed_psbt'], 'original_value': openchannelbump_res3['psbt'], 'new_value': NEW_VALUES_LIST['psbt_21'] },
            { 'data_keys': ['funding_serial'], 'original_value': openchannelbump_res1['funding_serial'], 'new_value': NEW_VALUES_LIST['funding_serial_3'] },
            { 'data_keys': ['funding_serial'], 'original_value': openchannelbump_res2['funding_serial'], 'new_value': NEW_VALUES_LIST['funding_serial_4'] },
            { 'data_keys': ['funding_serial'], 'original_value': openchannelbump_res3['funding_serial'], 'new_value': NEW_VALUES_LIST['funding_serial_5'] },
            
            { 'data_keys': ['signed_psbt'], 'original_value': signed_psbt_1['signed_psbt'], 'new_value': NEW_VALUES_LIST['psbt_22'] },
            { 'data_keys': ['tx'], 'original_value': openchannelsigned_res1['tx'], 'new_value': NEW_VALUES_LIST['ocs_tx_1'] },
            { 'data_keys': ['txid'], 'original_value': openchannelsigned_res1['txid'], 'new_value': NEW_VALUES_LIST['ocs_txid_1'] },
            { 'data_keys': ['any', 'signed_psbt'], 'original_value': signed_psbt_2['signed_psbt'], 'new_value': NEW_VALUES_LIST['psbt_23'] },
            { 'data_keys': ['tx'], 'original_value': openchannelsigned_res2['tx'], 'new_value': NEW_VALUES_LIST['ocs_tx_2'] },
            { 'data_keys': ['txid'], 'original_value': openchannelsigned_res2['txid'], 'new_value': NEW_VALUES_LIST['ocs_txid_2'] },
            { 'data_keys': ['psbt'], 'original_value': psbt_1, 'new_value': NEW_VALUES_LIST['psbt_24'] },
            { 'data_keys': ['psbt'], 'original_value': psbt_2, 'new_value': NEW_VALUES_LIST['psbt_25'] },
            { 'data_keys': ['any'], 'original_value': prev_utxos, 'new_value': example_utxos },
            
            { 'data_keys': ['unsigned_tx'], 'original_value': txdiscard_res1['unsigned_tx'], 'new_value': NEW_VALUES_LIST['unsigned_tx_3'] },
            { 'data_keys': ['unsigned_tx'], 'original_value': txdiscard_res2['unsigned_tx'], 'new_value': NEW_VALUES_LIST['unsigned_tx_4'] },
            { 'data_keys': ['tx'], 'original_value': txsend_res1['tx'], 'new_value': NEW_VALUES_LIST['txsend_tx_1'] },
            { 'data_keys': ['txid'], 'original_value': txsend_res1['txid'], 'new_value': NEW_VALUES_LIST['txsend_txid_1'] },
            { 'data_keys': ['psbt'], 'original_value': txsend_res1['psbt'], 'new_value': NEW_VALUES_LIST['psbt_24'] },
            { 'data_keys': ['tx'], 'original_value': txsend_res2['tx'], 'new_value': NEW_VALUES_LIST['txsend_tx_2'] },
            { 'data_keys': ['txid'], 'original_value': txsend_res2['txid'], 'new_value': NEW_VALUES_LIST['txsend_txid_2'] },
            { 'data_keys': ['psbt'], 'original_value': txsend_res2['psbt'], 'new_value': NEW_VALUES_LIST['psbt_26'] },
        ])
        l1.rpc.disconnect(l3.info['id'], True)
        l1.rpc.disconnect(l4.info['id'], True)
        l1.rpc.disconnect(l5.info['id'], True)
        bitcoind.generate_block(1)
        sync_blockheight(bitcoind, [l1, l3, l4, l5])
        logger.info('Channels Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating fundchannel and openchannel examples: {e}')


def generate_autoclean_delete_examples(l1, l2, l3, l4, l5, c12, c23):
    """Records autoclean and delete examples"""
    try:
        logger.info('Auto-clean and Delete Start...')
        global FUND_CHANNEL_AMOUNT_SAT
        l2.rpc.close(l5.info['id'])
        dfc_res1 = update_example(node=l2, method='dev-forget-channel', params={'id': l5.info['id']}, description=[f'Forget a channel by peer pubkey when only one channel exists with the peer:'])

        # Create invoices for delpay and delinvoice examples
        inv_l35 = l3.rpc.invoice('50000sat', 'lbl_l35', 'l35 description')
        inv_l36 = l3.rpc.invoice('50000sat', 'lbl_l36', 'l36 description')
        inv_l37 = l3.rpc.invoice('50000sat', 'lbl_l37', 'l37 description')

        # For MPP payment from l1 to l4; will use for delpay groupdid and partid example
        inv_l41 = l4.rpc.invoice('5000sat', 'lbl_l41', 'l41 description')
        l2.rpc.connect(l4.info['id'], 'localhost', l4.port)
        c24, c24res = l2.fundchannel(l4, FUND_CHANNEL_AMOUNT_SAT)
        l2.rpc.pay(l4.rpc.invoice(500000000, 'lbl balance l2 to l4', 'description send some sats l2 to l4')['bolt11'])
        # Create two routes; l1->l2->l3->l4 and l1->l2->l4
        route_l1_l4 = l1.rpc.getroute(l4.info['id'], '4000sat', 1)['route']
        route_l1_l2_l4 = [{'amount_msat': '1000sat', 'id': l2.info['id'], 'delay': 5, 'channel': c12},
                          {'amount_msat': '1000sat', 'id': l4.info['id'], 'delay': 5, 'channel': c24}]
        l1.rpc.sendpay(route_l1_l4, inv_l41['payment_hash'], amount_msat='5000sat', groupid=1, partid=1, payment_secret=inv_l41['payment_secret'])
        l1.rpc.sendpay(route_l1_l2_l4, inv_l41['payment_hash'], amount_msat='5000sat', groupid=1, partid=2, payment_secret=inv_l41['payment_secret'])
        # Close l2->l4 for initial state
        l2.rpc.close(l4.info['id'])
        l2.rpc.disconnect(l4.info['id'], True)

        # Delinvoice
        l1.rpc.pay(inv_l35['bolt11'])
        l1.rpc.pay(inv_l37['bolt11'])
        delinv_res1 = update_example(node=l3, method='delinvoice', params={'label': 'lbl_l36', 'status': 'unpaid'})

        # invoice already deleted, pay will fail; used for delpay failed example
        with pytest.raises(RpcError):
            l1.rpc.pay(inv_l36['bolt11'])

        listsendpays_l1 = l1.rpc.listsendpays()['payments']
        sendpay_g1_p1 = next((x for x in listsendpays_l1 if 'groupid' in x and x['groupid'] == 1 and 'partid' in x and x['partid'] == 2), None)
        delpay_res1 = update_example(node=l1, method='delpay', params={'payment_hash': listsendpays_l1[0]['payment_hash'], 'status': 'complete'})
        delpay_res2 = update_example(node=l1, method='delpay', params=[listsendpays_l1[-1]['payment_hash'], listsendpays_l1[-1]['status']])
        delpay_res3 = update_example(node=l1, method='delpay', params={'payment_hash': sendpay_g1_p1['payment_hash'], 'status': sendpay_g1_p1['status'], 'groupid': 1, 'partid': 2})
        delinv_res2 = update_example(node=l3, method='delinvoice', params={'label': 'lbl_l37', 'status': 'paid', 'desconly': True})

        # Delforward
        failed_forwards = l2.rpc.listforwards('failed')['forwards']
        local_failed_forwards = l2.rpc.listforwards('local_failed')['forwards']
        if len(local_failed_forwards) > 0 and 'in_htlc_id' in local_failed_forwards[0]:
            update_example(node=l2, method='delforward', params={'in_channel': c12, 'in_htlc_id': local_failed_forwards[0]['in_htlc_id'], 'status': 'local_failed'})
        if len(failed_forwards) > 0 and 'in_htlc_id' in failed_forwards[0]:
            update_example(node=l2, method='delforward', params={'in_channel': c12, 'in_htlc_id': failed_forwards[0]['in_htlc_id'], 'status': 'failed'})
        dfc_res2 = update_example(node=l2, method='dev-forget-channel', params={'id': l3.info['id'], 'short_channel_id': c23, 'force': True}, description=[f'Forget a channel by short channel id when peer has multiple channels:'])

        # Autoclean
        update_example(node=l2, method='autoclean-once', params=['failedpays', 1])
        update_example(node=l2, method='autoclean-once', params=['succeededpays', 1])
        update_example(node=l2, method='autoclean-status', params={'subsystem': 'expiredinvoices'})
        update_example(node=l2, method='autoclean-status', params={})
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['scid', 'channel'], 'original_value': c24, 'new_value': NEW_VALUES_LIST['c24'] },
            { 'data_keys': ['tx'], 'original_value': c24res['tx'], 'new_value': NEW_VALUES_LIST['c24_tx'] },
            { 'data_keys': ['txid'], 'original_value': c24res['txid'], 'new_value': NEW_VALUES_LIST['c24_txid'] },
            { 'data_keys': ['channel_id', 'account'], 'original_value': c24res['channel_id'], 'new_value': NEW_VALUES_LIST['c24_channel_id'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': delinv_res1['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_di_1'] },
            { 'data_keys': ['payment_hash'], 'original_value': delinv_res1['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_di_1'] },
            { 'data_keys': ['expires_at'], 'original_value': delinv_res1['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_860'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': delinv_res2['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_di_2'] },
            { 'data_keys': ['payment_hash'], 'original_value': delinv_res2['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_di_2'] },
            { 'data_keys': ['paid_at'], 'original_value': delinv_res2['paid_at'], 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['expires_at'], 'original_value': delinv_res2['expires_at'], 'new_value': NEW_VALUES_LIST['time_at_860'] },
            { 'data_keys': ['payment_preimage'], 'original_value': delinv_res2['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_di_1'] },

            { 'data_keys': ['payment_hash'], 'original_value': delpay_res1['payments'][0]['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_dp_1'] },
            { 'data_keys': ['payment_preimage'], 'original_value': delpay_res1['payments'][0]['payment_preimage'], 'new_value': NEW_VALUES_LIST['payment_preimage_dp_1'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': delpay_res1['payments'][0]['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_dp_1'] },
            { 'data_keys': ['created_at'], 'original_value': delpay_res1['payments'][0]['created_at'], 'new_value': NEW_VALUES_LIST['time_at_810'] },
            { 'data_keys': ['completed_at'], 'original_value': delpay_res1['payments'][0]['completed_at'], 'new_value': NEW_VALUES_LIST['time_at_820'] },
            { 'data_keys': ['any', 'payment_hash'], 'original_value': delpay_res2['payments'][0]['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_dp_2'] },
            { 'data_keys': ['any', 'bolt11'], 'original_value': delpay_res2['payments'][0]['bolt11'], 'new_value': NEW_VALUES_LIST['bolt11_dp_2'] },
            { 'data_keys': ['created_at'], 'original_value': delpay_res2['payments'][0]['created_at'], 'new_value': NEW_VALUES_LIST['time_at_830'] },
            { 'data_keys': ['completed_at'], 'original_value': delpay_res2['payments'][0]['completed_at'], 'new_value': NEW_VALUES_LIST['time_at_840'] },
            { 'data_keys': ['payment_hash'], 'original_value': delpay_res3['payments'][0]['payment_hash'], 'new_value': NEW_VALUES_LIST['payment_hash_dp_3'] },
            { 'data_keys': ['created_at'], 'original_value': delpay_res3['payments'][0]['created_at'], 'new_value': NEW_VALUES_LIST['time_at_850'] },
            { 'data_keys': ['completed_at'], 'original_value': delpay_res3['payments'][0]['completed_at'], 'new_value': NEW_VALUES_LIST['time_at_860'] },
            { 'data_keys': ['funding_txid'], 'original_value': dfc_res1['funding_txid'], 'new_value': NEW_VALUES_LIST['funding_txid_1'] },
            { 'data_keys': ['funding_txid'], 'original_value': dfc_res2['funding_txid'], 'new_value': NEW_VALUES_LIST['funding_txid_2'] },
        ])
        logger.info('Auto-clean and Delete Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating autoclean and delete examples: {e}')


def generate_backup_recovery_examples(node_factory, l4, l5, l6):
    """Node backup and recovery examples"""
    try:
        logger.info('Backup and Recovery Start...')

        # New node l13 used for recover example
        l13 = node_factory.get_node()

        update_example(node=l5, method='makesecret', params=['73636220736563726574'])
        update_example(node=l5, method='makesecret', params={'string': 'scb secret'})
        emergencyrecover_res1 = l4.rpc.emergencyrecover()
        emergencyrecover_res1['stubs'].sort()
        update_example(node=l4, method='emergencyrecover', params={}, res=emergencyrecover_res1, execute=False)
        
        backup_l4 = update_example(node=l4, method='staticbackup', params={})
        
        # Recover channels
        l4.stop()
        os.unlink(os.path.join(l4.daemon.lightning_dir, TEST_NETWORK, 'lightningd.sqlite3'))
        l4.start()
        time.sleep(1)
        recoverchannel_res1 = l4.rpc.recoverchannel(backup_l4['scb'])
        recoverchannel_res1['stubs'].sort()
        update_example(node=l4, method='recoverchannel', params={'scb': backup_l4['scb']}, res=recoverchannel_res1, execute=False)
        example_scb = [
            '000000000000000121bd30cac60f477f2c4267220b1702a6ec5780db34f9934fa94b8c0508bf3357035d2b1192dfba134e10e540875d366ebc8bc353d5aa766b80c090b39c3a5d885d00017f000001' + ('0001' * 17) + '0000000000000000000f42400003401000',
            '00000000000000027512083907c74ed3a045e9bf772b3d72948eb93daf84a1cee57108800451aaf2035d2b1192dfba134e10e540875d366ebc8bc353d5aa766b80c090b39c3a5d885d00017f000001' + ('0002' * 17) + '0000000100000000000f42400003401000',
            '0000000000000003ca8c620baf54a75d85bdedeb207f5c2ea78e568687dfd902730cc64c9065a519022d223620a359a47ff7f7ac447c85c46c923da53389221a0054c11c1e3ca31d5900017f000001' + ('0003' * 17) + '0000000000000000000f42400003401000',
            '00000000000000027512083907c74ed3a045e9bf772b3d72948eb93daf84a1cee57108800451aaf2035d2b1192dfba134e10e540875d366ebc8bc353d5aa766b80c090b39c3a5d885d00017f000001' + ('0004' * 17) + '0000000100000000000f42400003401000',
            '0000000000000003ca8c620baf54a75d85bdedeb207f5c2ea78e568687dfd902730cc64c9065a519022d223620a359a47ff7f7ac447c85c46c923da53389221a0054c11c1e3ca31d5900017f000001' + ('0005' * 17) + '0000000000000000000f42400003401000',
            '0000000000000003ca8c620baf54a75d85bdedeb207f5c2ea78e568687dfd902730cc64c9065a519022d223620a359a47ff7f7ac447c85c46c923da53389221a0054c11c1e3ca31d5900017f000001' + ('0006' * 17) + '0000000000000000000f42400003401000',
        ]
        # Emergency recover
        l5.stop()
        os.unlink(os.path.join(l5.daemon.lightning_dir, TEST_NETWORK, 'lightningd.sqlite3'))
        l5.start()
        time.sleep(1)
        emergencyrecover_res2 = l5.rpc.emergencyrecover()
        emergencyrecover_res2['stubs'].sort()
        update_example(node=l5, method='emergencyrecover', params={}, res=emergencyrecover_res2, execute=False)

        # Recover
        def get_hsm_secret(n):
            """Returns codex32 and hex"""
            try:
                hsmfile = os.path.join(n.daemon.lightning_dir, TEST_NETWORK, "hsm_secret")
                codex32 = subprocess.check_output(["tools/hsmtool", "getcodexsecret", hsmfile, "leet"]).decode('utf-8').strip()
                with open(hsmfile, "rb") as f:
                    hexhsm = f.read().hex()
                return codex32, hexhsm
            except Exception as e:
                logger.error(f'Error in getting hsm secret: {e}')

        _, l6hex = get_hsm_secret(l6)
        l13codex32, _ = get_hsm_secret(l13)
        update_example(node=l6, method='recover', params={'hsmsecret': l6hex})
        update_example(node=l13, method='recover', params={'hsmsecret': l13codex32})
        REPLACE_RESPONSE_VALUES.extend([
            { 'data_keys': ['hsmsecret'], 'original_value': l13codex32, 'new_value': NEW_VALUES_LIST['hsm_secret_cdx_1'] },
            { 'data_keys': ['scb'], 'original_value': backup_l4['scb'], 'new_value': example_scb },
        ])
        logger.info('Backup and Recovery Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating backup and recovery examples: {e}')


def generate_reckless_examples(l6):
    """Reckless plugin installation examples"""
    try:
        logger.info('Reckless Start...')
        REPLACE_REGEX_LIST = [item for item in REPLACE_RESPONSE_VALUES if isinstance(item['original_value'], re.Pattern)]
        response_1 = reckless([f'--network=regtest', '-j', '-v', 'search', 'testplugpass'], dir=l6.lightning_dir)
        response_1 = json.loads(f'{response_1.stdout.strip()}')
        for i in range(len(response_1['log'])):
            for item in REPLACE_REGEX_LIST:
                response_1['log'][i] = re.sub(item['original_value'], item['new_value'], response_1['log'][i])
        update_example(node=l6, method='reckless', params={'command':'search', 'target/subcommand': 'testplugpyproj'}, res=response_1, execute=False)
        response_2 = reckless([f'--network=regtest', '-j', '-v', 'install', '["testplugpass@v1", "testplugpyproj"]'], dir=l6.lightning_dir)
        response_2 = json.loads(f'{response_2.stdout.strip()}')
        for i in range(len(response_2['log'])):
            for item in REPLACE_REGEX_LIST:
                response_2['log'][i] = re.sub(item['original_value'], item['new_value'], response_2['log'][i])
        update_example(node=l6, method='reckless', params={'command':'install', 'target/subcommand': ["testplugpass@v1", "testplugpyproj"]}, res=response_2, execute=False)
        logger.info('Reckless Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating reckless examples: {e}')


def generate_list_examples(l1, l2, l3, c12, c23, inv_l31, inv_l32, offer_l23, inv_req_l1_l22):
    """Generates lists rpc examples"""
    try:
        logger.info('Lists Start...')

        # Transactions Lists
        update_example(node=l1, method='listfunds', params={})
        update_example(node=l2, method='listforwards', params={'in_channel': c12, 'out_channel': c23, 'status': 'settled'})
        update_example(node=l2, method='listforwards', params={})
        update_example(node=l2, method='listinvoices', params={'label': 'lbl_l21'})
        update_example(node=l2, method='listinvoices', params={})
        update_example(node=l1, method='listhtlcs', params=[c12])
        update_example(node=l1, method='listhtlcs', params={})
        update_example(node=l1, method='listsendpays', params={'bolt11': inv_l31['bolt11']})
        update_example(node=l1, method='listsendpays', params={})
        update_example(node=l1, method='listtransactions', params={})
        update_example(node=l2, method='listpays', params={'bolt11': inv_l32['bolt11']})
        update_example(node=l2, method='listpays', params={})
        update_example(node=l3, method='listclosedchannels', params={})

        # Network & Nodes Lists
        update_example(node=l2, method='listconfigs', params={'config': 'network'})
        update_example(node=l2, method='listconfigs', params={'config': 'experimental-dual-fund'})

        # Schema checker error: listconfigs.json: Additional properties are not allowed ('plugin' was unexpected)
        l2.rpc.jsonschemas = {}
        update_example(node=l2, method='listconfigs', params={})
        update_example(node=l2, method='listsqlschemas', params={'table': 'offers'})
        update_example(node=l2, method='listsqlschemas', params=['closedchannels'])
        update_example(node=l1, method='listpeerchannels', params={'id': l2.info['id']})
        update_example(node=l1, method='listpeerchannels', params={})
        update_example(node=l1, method='listchannels', params={'short_channel_id': c12})
        update_example(node=l1, method='listchannels', params={})
        update_example(node=l2, method='listnodes', params={'id': l3.info['id']})
        update_example(node=l2, method='listnodes', params={})
        update_example(node=l2, method='listpeers', params={'id': l3.info['id']})
        update_example(node=l2, method='listpeers', params={})
        update_example(node=l2, method='listdatastore', params={'key': ['test']})
        update_example(node=l2, method='listdatastore', params={'key': 'otherkey'})
        update_example(node=l2, method='listoffers', params={'active_only': True})
        update_example(node=l2, method='listoffers', params=[offer_l23['offer_id']])
        update_example(node=l2, method='listinvoicerequests', params=[inv_req_l1_l22['invreq_id']])
        update_example(node=l2, method='listinvoicerequests', params={})
        logger.info('Lists Done!')
    except TaskFinished:
        raise
    except Exception as e:
        logger.error(f'Error in generating lists examples: {e}')


@unittest.skipIf(GENERATE_EXAMPLES is not True, 'Generates examples for doc/schema/lightning-*.json files.')
def test_generate_examples(node_factory, bitcoind, executor):
    """Re-generates examples for doc/schema/lightning-*.json files"""
    try:
        global ALL_METHOD_NAMES, ALL_RPC_EXAMPLES, REGENERATING_RPCS, RPCS_STATUS

        def list_all_examples():
            """list all methods used in 'update_example' calls to ensure that all methods are covered"""
            try:
                global REGENERATING_RPCS
                methods = {}
                file_path = os.path.abspath(__file__)

                # Parse and traverse this file's content to list all methods & file names
                with open(file_path, "r") as file:
                    file_content = file.read()
                tree = ast.parse(file_content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'update_example':
                        for keyword in node.keywords:
                            if (keyword.arg == 'method' and isinstance(keyword.value, ast.Str)) or (keyword.arg == 'filename' and isinstance(keyword.value, ast.Str)):
                                method_name = keyword.value.s
                                if method_name not in methods:
                                    methods[method_name] = {'method': method_name, 'num_examples': 1, 'executed': 0}
                                else:
                                    methods[method_name]['num_examples'] += 1
                return list(methods.values())
            except Exception as e:
                logger.error(f'Error in listing all examples: {e}')

        def list_missing_examples():
            """Checks for missing example & log an error if missing."""
            try:
                global ALL_METHOD_NAMES
                for file_name in os.listdir('doc/schemas'):
                    if not file_name.endswith('.json'):
                        continue
                    file_name_str = str(file_name).replace('lightning-', '').replace('.json', '')
                    # Log an error if the method is not in the list
                    if file_name_str not in ALL_METHOD_NAMES:
                        logger.error(f'Missing Example {file_name_str}.')
            except Exception as e:
                logger.error(f'Error in listing missing examples: {e}')

        ALL_RPC_EXAMPLES = list_all_examples()
        ALL_METHOD_NAMES = [example['method'] for example in ALL_RPC_EXAMPLES]
        logger.info(f'This test can reproduce examples for {len(ALL_RPC_EXAMPLES)} methods: {ALL_METHOD_NAMES}')
        REGENERATING_RPCS = [rpc.strip() for rpc in os.getenv("REGENERATE").split(', ')] if os.getenv("REGENERATE") else ALL_METHOD_NAMES
        logger.info(f'Regenerating examples for: {REGENERATING_RPCS}')
        RPCS_STATUS = [False] * len(REGENERATING_RPCS)
        list_missing_examples()
        l1, l2, l3, l4, l5, l6, c12, c23, c25, c34, c23res = setup_test_nodes(node_factory, bitcoind)
        inv_l11, inv_l21, inv_l22, inv_l31, inv_l32, inv_l34 = generate_transactions_examples(l1, l2, l3, l4, l5, c25, bitcoind)
        rune_l21 = generate_runes_examples(l1, l2, l3)
        offer_l23, inv_req_l1_l22 = generate_offers_renepay_examples(l1, l2, inv_l21, inv_l34)
        generate_datastore_examples(l2)
        generate_bookkeeper_examples(l2, l3, c23res['channel_id'])
        # generate_askrene_examples(l1, l2, l3, c12, c23)
        generate_wait_examples(l1, l2, bitcoind, executor)
        generate_utils_examples(l1, l2, l3, l4, l5, l6, c23, c34, inv_l11, inv_l22, rune_l21, bitcoind)
        generate_splice_examples(node_factory, bitcoind)
        generate_channels_examples(node_factory, bitcoind, l1, l3, l4, l5)
        generate_autoclean_delete_examples(l1, l2, l3, l4, l5, c12, c23)
        generate_backup_recovery_examples(node_factory, l4, l5, l6)
        generate_reckless_examples(l6)
        generate_list_examples(l1, l2, l3, c12, c23, inv_l31, inv_l32, offer_l23, inv_req_l1_l22)
        update_examples_in_schema_files()
        logger.info('All examples generated successfully!')
    except TaskFinished as m:
        logger.info(m)
    except Exception as e:
        logger.error(e)

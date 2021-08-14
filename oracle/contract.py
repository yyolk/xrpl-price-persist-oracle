"""
xrpl-price-persist-oracle
"""
import os
import logging

from binascii import hexlify
from json import JSONDecodeError
from typing import List

import xrp_price_aggregate

from xrpl.account import get_next_valid_seq_number
from xrpl.asyncio.transaction.reliable_submission import XRPLReliableSubmissionException
from xrpl.clients import JsonRpcClient
from xrpl.ledger import get_fee, get_latest_validated_ledger_sequence
from xrpl.models.amounts import IssuedCurrencyAmount
from xrpl.models.transactions import Memo, TrustSetFlag
from xrpl.models.transactions import TrustSet
from xrpl.transaction import safe_sign_transaction, send_reliable_submission
from xrpl.utils import ripple_time_to_datetime
from xrpl.wallet import Wallet


XRPL_JSON_RPC_URL = os.environ["XRPL_JSON_RPC_URL"]
XRPL_NODE_ENVIRONMENT = os.environ["XRPL_NODE_ENVIRONMENT"]
MAINNET = XRPL_NODE_ENVIRONMENT == "Mainnet"
WALLET_SECRET = os.environ["WALLET_SECRET"]
# with our deployment being encapsulated within lambda and gh-actions, this
# provides verification of the git-sha as a deployment parameter that is public
# thorough the open source repo
GIT_COMMIT = os.environ["GIT_COMMIT"]

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Declare these outside the handler scope, for re-use in subsequent invocations
xrpl_client = JsonRpcClient(XRPL_JSON_RPC_URL)
wallet = Wallet(seed=WALLET_SECRET, sequence=None)
base_fee = get_fee(xrpl_client)


def gen_iou_amount(value: str) -> IssuedCurrencyAmount:
    """Returns a IssuedCurrencyAmount, at the value given.

    These are the issuers in both Test and Live XRPL environments:
        Livenet Issuers:
            r9PfV3sQpKLWxccdg3HL2FXKxGW2orAcLE == XRPL-Labs Oracle Account (USD)
            rhub8VRN55s94qWKDv6jmDy1pUykJzF3wq == GateHub (USD)
            rvYAfWj5gh67oV6fW32ZzP3Aw4Eubs59B == Bitstamp (USD)
        Testnet Issuers:
            rPWkTSpLJ2bumVKngjaeznSUUp4wj6tGuK == Random issuer on Testnet (FOO)

    Note:
        We could do some logic to inspect the accounts on each invocation (or
        cache it in outer scope for subsequent invocations). This would take
        more compute time. The livenet accounts usually also exist in the
        testnet. The logic would need to grab each last_transaction.

        I.e.,:

            >>> from xrpl.clients import JsonRpcClient
            >>> from xrpl.account import get_latest_transaction
            >>> client = JsonRpcClient("https://xrplcluster.com")
            >>> resp = get_latest_transaction("r9PfV3sQpKLWxccdg3HL2FXKxGW2orAcLE", client)
            >>> resp.result["transactions"][0]["tx"]["LimitAmount"]["value"]
            '0.82329'

    """
    return IssuedCurrencyAmount(
        currency="USD" if MAINNET else "FOO",
        issuer=(
            "r9PfV3sQpKLWxccdg3HL2FXKxGW2orAcLE"
            if MAINNET
            else "rPWkTSpLJ2bumVKngjaeznSUUp4wj6tGuK"
        ),
        value=value,
    )


def gen_memo(memo_data: str, memo_format: str, memo_type: str) -> Memo:
    """Utility for wrapping our encoding requirement"""
    return Memo(
        memo_data=hexlify(memo_data.encode("utf-8")).decode(),
        memo_format=hexlify(memo_format.encode("utf-8")).decode(),
        memo_type=hexlify(memo_type.encode("utf-8")).decode(),
    )


def gen_memos(raw_results_named) -> List[Memo]:
    """The attached memos, which will include our price data for verifiability

    This will generate the List of Memos for including in the TrustSet
    transaction. Each memo attached are results from the exchange set in the
    ``memo_type``.

        memo_format: Always "text/csv"
        memo_data: The values joined with commas (,) and truncated
        memo_type: Attached to each memo is the
                   exchange those rates originate from
                   Like ``rates:BITSTAMP``

    Args:
        raw_results_named: The expected input from xrp_price_aggregate

    Returns:
        List of Memo: The memos for attaching to this round's TrustSet
                      transaction

    """
    memos = []
    for exchange, values in raw_results_named.items():
        memos.append(
            Memo(
                memo_data=hexlify(
                    ";".join(map(lambda v: f"{v:.5f}", values)).encode("utf-8")
                ).decode(),
                memo_format=hexlify("text/csv".encode("utf-8")).decode(),
                memo_type=hexlify(f"rates:{exchange.upper()}".encode("utf-8")).decode(),
            )
        )
    return memos


def handler(
    event,
    _,  # we don't use the context
):
    """The handler for the function


    Alternative to the exhaustive search, one could use fast, optimized
    endpoints that don't include as many sources in this version of
    ``xrp_price_aggregate``

    I.e.:

        >>> # fast, include fast exchange clients that only use optimized price
        >>> # endpoints, the delay is higher since the response is so quick, and the
        >>> # price doesn't fluctuate as much, however we're not grabbing as many
        >>> # sources as exhaustive above
        >>> delay = 3
        >>> count = 5
        >>> xrp_agg = xrp_price_aggregate.as_dict(count=count, delay=delay, fast=True)

    """
    logger.debug("## EVENT")
    logger.debug(event)

    # exhaustive, include ccxt exchanges that provide more data than we'll use
    xrp_agg = xrp_price_aggregate.as_dict(count=3, delay=1.6, fast=False)

    logger.debug("xrp_agg is %s", xrp_agg)

    current_validated_ledger = get_latest_validated_ledger_sequence(client=xrpl_client)
    wallet.sequence = get_next_valid_seq_number(wallet.classic_address, xrpl_client)

    # Generate the memos we'll attach to the transaction, for independent
    # verification of results
    memos: List[Memo] = gen_memos(xrp_agg["raw_results_named"])
    # append in our GIT_COMMIT with a more brief but identical token of GITSHA
    # under an `oracle` prefix
    memos.append(gen_memo(GIT_COMMIT, "text/plain", "oracle:GITSHA"))

    # Generate the IssuedCurrencyAmount with the provided value
    iou_amount: IssuedCurrencyAmount = gen_iou_amount(str(xrp_agg["filtered_median"]))

    # Create the transaction, we're doing a TrustSet
    trustset_tx = TrustSet(
        account=wallet.classic_address,
        fee=base_fee,
        flags=TrustSetFlag.TF_SET_NO_RIPPLE,
        limit_amount=iou_amount,
        last_ledger_sequence=current_validated_ledger + 4,
        sequence=wallet.sequence,
        memos=memos,
    )
    # Sign the transaction
    trustset_tx_signed = safe_sign_transaction(trustset_tx, wallet)

    try:
        # The response from sending the transaction
        tx_response = send_reliable_submission(trustset_tx_signed, xrpl_client)

        # Log the results
        if tx_response.is_successful():
            logger.info(
                "Persisted last price $%s at %s",
                xrp_agg["filtered_median"],
                ripple_time_to_datetime(tx_response.result["date"]),
            )
        else:
            # NOTE: if the submission errored, we could raise an exception
            #       instead of just logger.error(...)
            #       Lambda will retry the function twice for a total of 3 times
            logger.error("Unsucessful transaction response: %s", tx_response)
    except XRPLReliableSubmissionException as err:
        if str(err).startswith("Transaction failed, telINSUF_FEE_P"):
            # we'll need to retry
            raise err
        if str(err).startswith("Transaction failed, tefPAST_SEQ"):
            # we should retry, we didn't match our expected SLA
            return
        if str(err).startswith("Transaction failed, terQUEUED"):
            # our txn will send, this is fine?
            return
        logger.error("Got unexpected XRPLReliableSubmissionException: %s", err)
    except JSONDecodeError as err:
        logger.error(
            (
                "Got a JSONDecodeError %s, retrying the transaction by"
                " failing this execution"
            ),
            err,
        )
        raise err

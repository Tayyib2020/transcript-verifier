"""Direct-mode tests for TranscriptVerifier."""

import hashlib


CONTRACT_PATH = "contracts/transcript_verifier.py"


def digest(transcript: str) -> str:
    return "0x" + hashlib.sha256(transcript.encode("utf-8")).hexdigest()


def summary_digest(summary: str) -> str:
    return "0x" + hashlib.sha256(summary.encode("utf-8")).hexdigest()


def verification_id(transcript_hash: str, summary_hash: str) -> str:
    return "0x" + hashlib.sha256(f"{transcript_hash}:{summary_hash}".encode("utf-8")).hexdigest()


def test_accurate_summary_is_stored(direct_vm, direct_deploy):
    transcript = "The team is prioritizing Clarke's readiness before release."
    summary = "The team is prioritizing Clarke's readiness before releasing."
    direct_vm.mock_llm(r"transcript-summary adjudicator", {
        "decision": "ACCEPTED",
        "reason": "The candidate preserves the readiness condition.",
    })

    contract = direct_deploy(CONTRACT_PATH)
    contract.submit_verification(transcript, summary, digest(transcript))

    assert contract.has_successful_verification(digest(transcript)) is True
    record = contract.get_verification(digest(transcript))
    assert record["status"] == "ACCEPTED"
    assert record["summary"] == summary


def test_fabricated_summary_is_rejected(direct_vm, direct_deploy):
    transcript = "The team discussed the roadmap."
    summary = "The team announced a launch next week."
    direct_vm.mock_llm(r"transcript-summary adjudicator", {
        "decision": "REJECTED",
        "reason": "The launch announcement is not in the transcript.",
    })

    contract = direct_deploy(CONTRACT_PATH)
    contract.submit_verification(transcript, summary, digest(transcript))

    assert contract.has_successful_verification(digest(transcript)) is False
    assert contract.get_verification(digest(transcript))["status"] == "REJECTED"


def test_changed_certainty_is_rejected(direct_vm, direct_deploy):
    transcript = "The community testnet may open later; no date is confirmed."
    summary = "The community testnet will open later."
    direct_vm.mock_llm(r"transcript-summary adjudicator", {
        "decision": "REJECTED",
        "reason": "The summary changes a possibility into a confirmed plan.",
    })

    contract = direct_deploy(CONTRACT_PATH)
    contract.submit_verification(transcript, summary, digest(transcript))
    assert contract.has_successful_verification(digest(transcript)) is False


def test_hash_and_input_validation(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT_PATH)

    with direct_vm.expect_revert("transcript_hash does not match"):
        contract.submit_verification("Transcript A", "Summary", digest("Transcript B"))

    with direct_vm.expect_revert("transcript must be a non-empty string"):
        contract.submit_verification("", "Summary", digest(""))


def test_duplicate_hash_cannot_overwrite(direct_vm, direct_deploy):
    transcript = "The AMA covered the roadmap."
    summary = "The AMA covered the roadmap."
    direct_vm.mock_llm(r"transcript-summary adjudicator", {
        "decision": "ACCEPTED",
        "reason": "The summary matches the transcript.",
    })

    contract = direct_deploy(CONTRACT_PATH)
    contract.submit_verification(transcript, summary, digest(transcript))

    with direct_vm.expect_revert("A verification already exists"):
        contract.submit_verification(transcript, "A different summary", digest(transcript))


def test_different_summary_attempts_have_distinct_identities(direct_vm, direct_deploy):
    transcript = "The community testnet may open later; no date is confirmed."
    first_summary = "The community testnet may open later."
    second_summary = "The community testnet has opened today."
    direct_vm.mock_llm(r"transcript-summary adjudicator", {
        "decision": "REJECTED",
        "reason": "The candidate changes the certainty of the transcript.",
    })

    contract = direct_deploy(CONTRACT_PATH)
    transcript_hash = digest(transcript)
    first_id = verification_id(transcript_hash, summary_digest(first_summary))
    second_id = verification_id(transcript_hash, summary_digest(second_summary))
    assert first_id != second_id
    contract.submit_verification_attempt(transcript, first_summary, transcript_hash, first_id)

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"transcript-summary adjudicator", {
        "decision": "ACCEPTED",
        "reason": "The second candidate is faithful.",
    })
    contract.submit_verification_attempt(transcript, second_summary, transcript_hash, second_id)

    assert contract.get_verification(first_id)["status"] == "REJECTED"
    assert contract.get_verification(second_id)["status"] == "ACCEPTED"
    assert contract.get_verification(second_id)["transcript_hash"] == transcript_hash
    assert contract.get_verification(second_id)["summary_hash"] == summary_digest(second_summary)


def test_validator_compares_decision_not_reasoning(direct_vm, direct_deploy):
    transcript = "The team is investigating a possible partnership."
    summary = "The team is investigating a possible partnership."
    direct_vm.mock_llm(r"transcript-summary adjudicator", {
        "decision": "ACCEPTED",
        "reason": "Leader wording",
    })

    contract = direct_deploy(CONTRACT_PATH)
    contract.submit_verification(transcript, summary, digest(transcript))

    direct_vm.clear_mocks()
    direct_vm.mock_llm(r"transcript-summary adjudicator", {
        "decision": "ACCEPTED",
        "reason": "Validator wording differs but the decision agrees.",
    })
    assert direct_vm.run_validator() is True

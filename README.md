# TranscriptVerifier — GenLayer Intelligent Contract

`TranscriptVerifier` is a standalone GenLayer Intelligent Contract that uses
AI-powered validator consensus to decide whether a proposed summary faithfully
represents a supplied transcript. It is Deliverable 1 of the GenLayer Live
Transcript project and is intentionally independent of any future web app.

## What it verifies

The evaluator rejects summaries that fabricate announcements, change certainty,
contradict the transcript, materially remove context, or misrepresent speaker
meaning. It may accept substantial paraphrasing when important meaning is
preserved.

This verifies summary fidelity to the supplied transcript. It does not prove
that the transcript is truthful, that speakers were correctly identified, or
that any claim in the transcript is factually correct.

## Deployed TranscriptVerifier V2

The attempt-aware V2 contract used by Signal Ledger is deployed on GenLayer
Bradbury at:

`0x4DEfE1bbE75C59FcD2264EaCb75096f3CD659f5B`

## A reusable semantic-fidelity primitive

TranscriptVerifier is not limited to GenLayer AMAs. It is a general-purpose
verification primitive for checking whether an AI-generated summary faithfully
represents a source transcript. Possible applications include:

- AMA summaries
- meeting summaries
- governance calls
- interviews
- research transcripts
- community calls
- earnings calls
- archived discussions

## Standalone structure

```text
transcript-verifier/
├── contracts/
│   └── transcript_verifier.py
├── scripts/
│   └── hash_transcript.py
├── tests/
│   ├── test_cases.json
│   └── test_direct.py
└── README.md
```

## Contract interface

### `submit_verification(transcript, proposed_summary, transcript_hash)`

Submits one candidate summary for one transcript. The contract validates input,
recomputes SHA-256 over the exact UTF-8 transcript, rejects a mismatched hash,
rejects duplicate hashes, and runs an LLM adjudicator through
`gl.vm.run_nondet_unsafe`. Validators independently adjudicate the same pair
and consensus compares only the stable `decision` field (`ACCEPTED` or
`REJECTED`), allowing explanations to differ. The full transcript is not
persisted.

If consensus cannot agree, GenLayer leaves the transaction undetermined and the
record is not written.

### `get_verification(transcript_hash)`

Returns `transcript_hash`, `summary`, `status`, `reason`, `submitted_at`, and
`submitter`, or `{}` when no record exists or the hash format is invalid.

### `has_successful_verification(transcript_hash)`

Returns `true` only when the stored status for the hash is `ACCEPTED`.

## State and hashing

Persistent state is a `TreeMap[str, VerificationRecord]` keyed by normalized
transcript hash. Each record stores only the proposed summary, decision,
adjudication reason, deterministic transaction time, and caller address.

The hash protocol is:

```text
transcript_hash = "0x" + SHA256(exact UTF-8 transcript bytes).hexdigest()
```

Hashing happens in the client before submission and is recomputed inside the
contract. Do not trim, normalize line endings, or otherwise change the
transcript between hashing and submission. The helper computes the digest for a
UTF-8 file:

```bash
python scripts/hash_transcript.py transcript.txt
```

A matching hash proves only that the evaluated string has not changed. It does
not establish that the transcript itself is accurate or complete.

The first consensus result wins for the legacy transcript-hash identity; later
submissions cannot overwrite it.

### `submit_verification_attempt(transcript, proposed_summary, transcript_hash, verification_id)`

The attempt-aware method preserves `transcript_hash` as the SHA-256 digest of
the exact canonical transcript while allowing a different summary to receive a
different deterministic identity. The required identity is:

```text
summary_hash = "0x" + SHA256(exact proposed summary UTF-8 bytes).hexdigest()
verification_id = "0x" + SHA256(transcript_hash + ":" + summary_hash).hexdigest()
```

The contract recomputes both values and rejects mismatches. This method is part
of the deployed Bradbury V2 contract above.

## Why GenLayer is appropriate

Summary fidelity is semantic adjudication. Deterministic string comparison
cannot reliably recognize faithful paraphrases, detect certainty changes, or
decide whether omitted context changes meaning. GenLayer lets independent
LLM-capable validators make that judgment and uses consensus for the stable
decision.

This is not a speech-to-text contract. Transcription, full archive storage, and
summary generation remain off-chain application concerns.

## Equivalence mechanism

The contract follows the current custom leader/validator pattern:

- The leader calls `gl.nondet.exec_prompt(..., response_format="json")`.
- Each validator independently runs the same adjudication prompt.
- The validator checks response shape and compares only `decision`.
- Free-form `reason` text is not compared because valid validators may explain
  the same decision differently.

`strict_eq` is intentionally not used: the official documentation warns that
exact equality is inappropriate for non-deterministic LLM output.

## Test examples

`tests/test_cases.json` contains five AMA-style examples:

1. Accurate summary — accepted.
2. Fabricated announcement — rejected.
3. Possibility changed into certainty — rejected.
4. Heavy paraphrase preserving meaning — accepted.
5. Important context removed — rejected.

## Local testing

Prerequisites from the current GenLayer documentation:

- Python 3.12+
- `genlayer-test`
- Optional `genvm-lint` for static contract checks

From this directory:

```bash
pip install genlayer-test
pytest tests/ -v
genvm-lint check contracts/transcript_verifier.py
```

The direct tests mock `gl.nondet.exec_prompt`, so they do not call a real LLM
or require Studio. Before deployment, run a Studio-mode test with configured
validators to exercise network consensus.

## Studio and testnet workflow

The current documented progression is localnet → Studionet → Testnet Bradbury.
Bradbury is the appropriate environment for real AI/LLM workloads.

### Local Studio

```bash
npm install -g genlayer
genlayer init
genlayer up
```

Then run Studio-mode tests:

```bash
gltest tests/ -v -s --network localnet
```

You can also upload `contracts/transcript_verifier.py` to the hosted Studio at
`https://studio.genlayer.com/`, deploy it with no constructor arguments, and
exercise the public methods in the UI.

### Testnet Bradbury

Use a funded GenLayer account and select the network before deploying:

```bash
genlayer network set testnet-bradbury
genlayer deploy --contract contracts/transcript_verifier.py
```

If your installed CLI exposes the legacy shorthand, follow `genlayer --help`;
the current CLI form is `genlayer network set testnet-bradbury`. Save both the
deployment transaction hash and the resulting contract address. LLM
transactions can take time and require sufficient fees; wait for
accepted/finalized status and do not treat a submitted hash alone as a
completed verification.

After deployment, interact using the CLI:

```bash
genlayer schema <CONTRACT_ADDRESS>
genlayer call <CONTRACT_ADDRESS> has_successful_verification --args <HASH>
genlayer call <CONTRACT_ADDRESS> get_verification --args <HASH>
genlayer write <CONTRACT_ADDRESS> submit_verification --args <TRANSCRIPT> <SUMMARY> <HASH>
```

For long values, use the GenLayer JS/Python SDK or Studio UI rather than shell
quoting. Never put a private key in this repository or browser code.

### Bradbury V2 deployment

The attempt-aware TranscriptVerifier V2 contract is deployed on GenLayer
Testnet Bradbury at:

`0x4DEfE1bbE75C59FcD2264EaCb75096f3CD659f5B`

It supports `submit_verification`, `submit_verification_attempt`,
`get_verification`, and `has_successful_verification`.

## Submission metadata

Suggested title:

> TranscriptVerifier — Consensus-Based Verification of AI Summaries Against Exact Transcripts

Suggested description:

> TranscriptVerifier is a GenLayer Intelligent Contract for community-generated
> AMA archives. It receives an exact transcript, a proposed AI summary, and a
> SHA-256 transcript identifier. LLM-capable GenLayer validators independently
> judge whether the summary preserves important meaning, avoids fabrication,
> preserves certainty and context, and reasonably represents the transcript.
> Consensus compares the stable accepted/rejected decision while allowing
> validator reasoning to differ. The contract stores only compact verification
> metadata keyed by the transcript hash, not the full transcript. GenLayer is
> necessary because summary faithfulness is semantic judgment rather than exact
> string matching; the result verifies the summary against the transcript, not
> that every spoken statement is true.

## Configuration and limitations

The contract has no constructor arguments and no secrets. The LLM provider/model
is supplied by the GenLayer validator environment, not by this repository.

Important limitations:

- LLM adjudication is judgment-based and can be conservative or disagree on
  ambiguous cases; consensus may rotate or become undetermined.
- Input sizes are bounded to keep prompts and fees practical. Network/runtime
  limits may be lower.
- The contract cannot recover missing audio or prove speaker identity or factual
  truth.
- A hash is exact-integrity evidence, not a truth oracle.

## Documentation basis

The implementation follows the current official GenLayer documentation for IC
class/decorator/storage syntax, `gl.nondet.exec_prompt`, custom equivalence via
`gl.vm.run_nondet_unsafe`, transaction metadata, direct-mode testing with
`genlayer-test`, and CLI/Testnet Bradbury deployment.

This folder is the complete standalone Deliverable 1. A future transcript
application must reuse the deployed address and must not deploy a replacement
contract.

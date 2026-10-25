from pathlib import Path

path = Path("src/App.tsx")

text = path.read_text(encoding="utf-8")

# =========================================================

# 1. Add review state inside MatchCard

# =========================================================

preview_marker = """  } | null>(null);"""

if preview_marker not in text:

    raise SystemExit("ERROR: preview state marker not found")

if "const [reviewStatus" not in text:

    review_state = """

  const [reviewStatus, setReviewStatus] = useState<

    "PENDING" | "CONFIRMED" | "REJECTED"

  >(

    match.review_status === "CONFIRMED"

      ? "CONFIRMED"

      : match.review_status === "REJECTED"

        ? "REJECTED"

        : "PENDING"

  );

  const [reviewComment, setReviewComment] =

    useState<string>(

      match.review_comment || ""

    );

  const [reviewSaved, setReviewSaved] =

    useState(false);

  const saveReview = () => {

    match.review_status = reviewStatus;

    match.review_comment = reviewComment;

    match.reviewed_at = new Date().toISOString();

    setReviewSaved(true);

  };

"""

    text = text.replace(

        preview_marker,

        preview_marker + review_state,

        1,

    )

# =========================================================

# 2. Add review panel before closing match-card-body

# =========================================================

body_marker = """          </div>

        </div>

      </article>"""

if body_marker not in text:

    raise SystemExit(

        "ERROR: MatchCard body closing marker not found"

    )

review_panel = """          <div className="review-panel">

            <div className="review-panel-header">

              <div>

                <span>HUMAN REVIEW</span>

                <h3>Review Decision</h3>

              </div>

              <span

                className={`review-status review-${reviewStatus.toLowerCase()}`}

              >

                {reviewStatus}

              </span>

            </div>

            <div className="review-actions">

              <button

                type="button"

                className={

                  reviewStatus === "PENDING"

                    ? "review-button active pending"

                    : "review-button pending"

                }

                onClick={() => {

                  setReviewStatus("PENDING");

                  setReviewSaved(false);

                }}

              >

                PENDING

              </button>

              <button

                type="button"

                className={

                  reviewStatus === "CONFIRMED"

                    ? "review-button active confirmed"

                    : "review-button confirmed"

                }

                onClick={() => {

                  setReviewStatus("CONFIRMED");

                  setReviewSaved(false);

                }}

              >

                ✓ CONFIRM

              </button>

              <button

                type="button"

                className={

                  reviewStatus === "REJECTED"

                    ? "review-button active rejected"

                    : "review-button rejected"

                }

                onClick={() => {

                  setReviewStatus("REJECTED");

                  setReviewSaved(false);

                }}

              >

                ✕ REJECT

              </button>

            </div>

            <div className="review-comment">

              <label htmlFor={`review-comment-${index}`}>

                REVIEWER COMMENT

              </label>

              <textarea

                id={`review-comment-${index}`}

                value={reviewComment}

                onChange={(event) => {

                  setReviewComment(event.target.value);

                  setReviewSaved(false);

                }}

                placeholder="Add a review note..."

                rows={3}

              />

            </div>

            <div className="review-footer">

              <button
type="button"

                className="save-review-button"

                onClick={saveReview}

              >

                SAVE REVIEW

              </button>

              {reviewSaved && (

                <span className="review-saved">

                  ✓ Review saved

                </span>

              )}

            </div>

          </div>

"""

text = text.replace(

    body_marker,

    review_panel + body_marker,

    1,

)

path.write_text(text, encoding="utf-8")

print("REVIEW STATE: OK")

print("REVIEW ACTIONS: OK")

print("REVIEW COMMENT: OK")

print("SAVE REVIEW: OK")

print("PATCHED OK")
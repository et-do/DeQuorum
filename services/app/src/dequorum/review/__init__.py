"""Review: signed votes + service that tallies them and transitions contribution status.

Note: `ReviewService` is intentionally NOT re-exported here. Eagerly loading
`service` from this `__init__` creates a circular import with `dequorum.knowledge`
(which needs `Vote` from this package, but loading the package would also load
`service`, which needs `ContributionStore`). Import it directly:

    from dequorum.review.service import ReviewService
"""

from dequorum.review.vote import VALID_SCORES, Vote

__all__ = ["VALID_SCORES", "Vote"]

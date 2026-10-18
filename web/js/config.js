/* Site configuration -- the one file to edit after deploying worker/. */
(function () {
  "use strict";
  window.Spaceships = window.Spaceships || {};
  window.Spaceships.config = {
    // URL of the deployed claim service (worker/), no trailing slash,
    // e.g. "https://spaceships-claims.<account>.workers.dev".
    // null = claims aren't open yet; the pages say so instead of erroring.
    CLAIM_ENDPOINT: "https://spaceships-claims.johnwinstong.workers.dev",
  };
})();

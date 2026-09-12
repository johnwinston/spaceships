/* "Claim this ship" panel on the player page. */
(function () {
  "use strict";

  function $(id) { return document.getElementById(id); }

  function whenText(iso) {
    if (!iso) return "";
    try {
      return new Date(iso).toLocaleDateString(undefined,
        { year: "numeric", month: "short", day: "numeric" });
    } catch (e) { return ""; }
  }

  function describe(claim) {
    var who = claim.name ? "claimed by " + claim.name : "claimed";
    var when = whenText(claim.claimedAt);
    return when ? who + " on " + when : who;
  }

  function setStatus(text, isError) {
    var el = $("claimstatus");
    el.textContent = text;
    el.className = isError ? "error" : "";
  }

  function render(claim) {
    if (claim) {
      setStatus(describe(claim) + ".");
      $("claimbtn").textContent = "Update name";
      $("claimhint").textContent = "Hold the card? Enter its code to change the name.";
    } else {
      setStatus("Unclaimed. Bought this card? It's yours to claim.");
      $("claimbtn").textContent = "Claim";
      $("claimhint").textContent = "";
    }
  }

  async function submit(ship, form) {
    var btn = $("claimbtn");
    btn.disabled = true;
    try {
      var result = await window.Spaceships.claims.claim(
        ship.id, $("claimcode").value, $("claimname").value);
      if (result.ok) {
        render(result.claim);
        setStatus((result.updated ? "Name updated. " : "Claimed! ") + describe(result.claim) + ".");
        $("claimcode").value = "";
      } else {
        setStatus(result.message, true);
      }
    } catch (e) {
      setStatus("Couldn't reach the claim service. Try again in a moment.", true);
    } finally {
      btn.disabled = false;
    }
    return false;
  }

  async function init(ship, prefillCode) {
    var section = $("claim");
    if (!section || !ship || !ship.id || !Number(ship.edition)) return; // demo ships aren't cards
    section.hidden = false;
    var C = window.Spaceships.claims;
    if (!C.available()) {
      setStatus("Claims open soon.");
      return;
    }
    var form = $("claimform");
    form.hidden = false;
    if (prefillCode) $("claimcode").value = prefillCode;
    form.onsubmit = function (ev) { ev.preventDefault(); submit(ship, form); };
    try {
      render(await C.get(ship.id));
    } catch (e) {
      setStatus("Couldn't reach the claim service. Try again in a moment.", true);
    }
  }

  window.Spaceships = window.Spaceships || {};
  window.Spaceships.claimUI = { init: init };
})();

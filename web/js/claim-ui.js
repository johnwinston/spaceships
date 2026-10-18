/* "Claim this ship" panel on the player page.
 *
 * The claim QR John hands a buyer opens this page with the code already
 * filled in (`c=`); the buyer adds a wallet address and the claim
 * service sends the ship's NFT there from the vault. */
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

  /* "In wallet AbCd…WxYz · view the NFT", or hidden when not sent yet. */
  function showNft(claim) {
    var el = $("claimnft");
    var sent = Boolean(claim && claim.wallet);
    el.hidden = !sent;
    $("walletfield").hidden = sent;
    $("claimwallet").required = !sent; // a hidden required field would block "Update name"
    $("wallethelp").hidden = sent;
    if (!sent) return;
    var C = window.Spaceships.claims;
    el.textContent = "";
    el.appendChild(document.createTextNode("In wallet " + C.shortAddress(claim.wallet)));
    if (claim.asset) {
      el.appendChild(document.createTextNode(" · "));
      var a = document.createElement("a");
      a.href = C.explorerUrl(claim.asset, claim.cluster);
      a.target = "_blank";
      a.rel = "noopener";
      a.textContent = "view the NFT";
      el.appendChild(a);
    }
  }

  function render(claim) {
    showNft(claim);
    if (claim) {
      setStatus(describe(claim) + ".");
      $("claimbtn").textContent = claim.wallet ? "Update name" : "Send the NFT";
      $("claimhint").textContent = claim.wallet
        ? "Hold the claim code? Enter it to change the name."
        : "Add a wallet address to receive this ship's NFT.";
    } else {
      setStatus("Unclaimed. Bought this card? It's yours to claim.");
      $("claimbtn").textContent = "Claim";
      $("claimhint").textContent = "";
    }
  }

  async function submit(ship) {
    var btn = $("claimbtn");
    btn.disabled = true;
    var wallet = $("walletfield").hidden ? "" : $("claimwallet").value.trim();
    if (wallet) setStatus("Sending your ship…");
    try {
      var result = await window.Spaceships.claims.claim(
        ship.id, $("claimcode").value, $("claimname").value, wallet);
      if (result.ok) {
        render(result.claim);
        var lead = result.claim.wallet && wallet ? "Sent! "
          : result.updated ? "Name updated. " : "Claimed! ";
        setStatus(lead + describe(result.claim) + ".");
        $("claimcode").value = "";
      } else {
        if (result.claim) showNft(result.claim);
        setStatus(result.message, true);
      }
    } catch (e) {
      setStatus("Couldn't reach the claim service. Try again in a moment.", true);
    } finally {
      btn.disabled = false;
    }
  }

  /* Phantom injects window.phantom.solana in its own in-app browser and
   * as a desktop extension; there, offer to fill the address from it. */
  function setUpPhantom() {
    var provider = window.phantom && window.phantom.solana;
    if (provider && provider.isPhantom) {
      var btn = $("phantombtn");
      btn.hidden = false;
      btn.onclick = async function () {
        try {
          var res = await provider.connect();
          $("claimwallet").value = res.publicKey.toString();
        } catch (e) {
          setStatus("Phantom didn't connect. You can paste the address instead.", true);
        }
      };
    }
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
    setUpPhantom();
    form.onsubmit = function (ev) { ev.preventDefault(); submit(ship); };
    try {
      render(await C.get(ship.id));
    } catch (e) {
      setStatus("Couldn't reach the claim service. Try again in a moment.", true);
    }
  }

  window.Spaceships = window.Spaceships || {};
  window.Spaceships.claimUI = { init: init };
})();

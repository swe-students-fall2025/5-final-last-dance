document.addEventListener("DOMContentLoaded", function () {
  var searchInput = document.getElementById("job-search");
  var chips = document.querySelectorAll(".chip");
  var cards = document.querySelectorAll("#job-board-cards .card--board");

  var activeFilter = "all";
  var activeTypeFilter = null;

  function normalize(text) {
    return (text || "").toLowerCase();
  }

  function applyFilters() {
    var query = normalize(searchInput ? searchInput.value : "");

    cards.forEach(function (card) {
      var title = normalize(card.querySelector("h3")?.textContent);
      var company = normalize(card.dataset.company);
      var location = normalize(card.dataset.location);
      var tags = normalize(card.dataset.tags);
      var type = card.dataset.type;
      var isRemote = card.dataset.remote === "true";
      var match = parseInt(card.dataset.match || "0", 10);

      var visible = true;

      if (query) {
        var haystack = title + " " + company + " " + location + " " + tags;
        if (!haystack.includes(query)) visible = false;
      }

      if (activeFilter === "top-matches" && match < 70) visible = false;
      if (activeFilter === "remote" && !isRemote) visible = false;

      if (activeTypeFilter && type !== activeTypeFilter) visible = false;

      card.style.display = visible ? "" : "none";
    });
  }

  if (searchInput) {
    searchInput.addEventListener("input", function () {
      applyFilters();
    });
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      chips.forEach(function (c) {
        c.classList.remove("chip--active");
      });
      chip.classList.add("chip--active");

      activeFilter = chip.dataset.filter || activeFilter;
      activeTypeFilter = chip.dataset.filterType || null;

      if (chip.dataset.filter === "all") {
        activeFilter = "all";
        activeTypeFilter = null;
      }

      applyFilters();
    });
  });

  // Favorite button functionality
  var favoriteButtons = document.querySelectorAll(".card__favorite, .job-detail__favorite");
  favoriteButtons.forEach(function (button) {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();

      var companySlug = button.dataset.companySlug;
      var identifier = button.dataset.identifier;

      if (!companySlug || !identifier) {
        return;
      }

      // Toggle visual state immediately for better UX
      var wasActive = button.classList.contains("card__favorite--active") || 
                      button.classList.contains("job-detail__favorite--active");
      
      // Identifier is already URL-encoded from the template, use it directly
      fetch("/favorite/" + companySlug + "/" + identifier, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      })
        .then(function (response) {
          return response.json();
        })
        .then(function (data) {
          if (data.favorited) {
            button.classList.add("card__favorite--active", "job-detail__favorite--active");
            button.textContent = "♥";
            button.setAttribute("aria-label", "Unfavorite job");
          } else {
            button.classList.remove("card__favorite--active", "job-detail__favorite--active");
            button.textContent = "♡";
            button.setAttribute("aria-label", "Favorite job");
          }
        })
        .catch(function (error) {
          console.error("Error toggling favorite:", error);
          // Revert visual state on error
          if (wasActive) {
            button.classList.add("card__favorite--active", "job-detail__favorite--active");
            button.textContent = "♥";
          } else {
            button.classList.remove("card__favorite--active", "job-detail__favorite--active");
            button.textContent = "♡";
          }
        });
    });
  });
});
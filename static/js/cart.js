(function () {
  "use strict";

  function updateCartCount(count) {
    var badge = document.getElementById("cart-count");
    if (!badge) {
      return;
    }
    badge.textContent = count;
    badge.hidden = count === 0;
  }

  function updateCartPage(container, data) {
    var row = container.closest("[data-cart-item]");
    if (data.quantity === 0 || data.removed) {
      row.remove();
      if (!document.querySelector("[data-cart-item]")) {
        document.getElementById("cart-table").hidden = true;
        document.getElementById("cart-total").hidden = true;
        document.getElementById("checkout-link").hidden = true;
        document.getElementById("cart-empty").hidden = false;
      }
    } else {
      row.querySelector(".cart-item-quantity").textContent = data.quantity;
      row.querySelector(".cart-item-subtotal").textContent = data.subtotal;
      var quantityInputs = row.querySelectorAll('input[name="quantity"]');
      quantityInputs[0].value = data.quantity - 1;
      quantityInputs[1].value = data.quantity + 1;
      row.querySelectorAll("button").forEach(function (control) {
        control.disabled = false;
      });
    }
    document.getElementById("cart-total").textContent = "Total: €" + data.total;
  }

  function renderControls(container, quantity, stock) {
    var csrfToken = container.querySelector("input[name=csrfmiddlewaretoken]").value;
    var addUrl = container.querySelector("form[action*='/add/']").action;
    var updateUrl = container.querySelector("form[action*='/update/']");
    updateUrl = updateUrl ? updateUrl.action : addUrl.replace("/add/", "/update/");
    var unavailable = stock === null || stock === 0;

    if (quantity === 0) {
      container.innerHTML =
        '<form method="post" action="' + addUrl + '" class="cart-ajax-form">' +
        '<input type="hidden" name="csrfmiddlewaretoken" value="' + csrfToken + '">' +
        '<button class="btn btn-primary btn-sm"' + (unavailable ? " disabled" : "") + '>Add to cart</button>' +
        '</form><div class="cart-error text-danger small" role="alert" hidden></div>';
      return;
    }

    container.innerHTML =
      '<div class="btn-group" role="group" aria-label="Cart quantity controls">' +
      '<form method="post" action="' + updateUrl + '" class="d-inline cart-ajax-form">' +
      '<input type="hidden" name="csrfmiddlewaretoken" value="' + csrfToken + '">' +
      '<input type="hidden" name="quantity" value="' + (quantity - 1) + '">' +
      '<button class="btn btn-outline-primary btn-sm">-</button></form>' +
      '<div class="cart-quantity" style="padding:5px;">' + quantity + "</div>" +
      '<form method="post" action="' + addUrl + '" class="d-inline cart-ajax-form">' +
      '<input type="hidden" name="csrfmiddlewaretoken" value="' + csrfToken + '">' +
      '<button class="btn btn-outline-primary btn-sm"' + (unavailable ? " disabled" : "") + '>+</button></form>' +
      '</div><div class="cart-error text-danger small" role="alert" hidden></div>';
  }

  document.addEventListener("submit", function (event) {
    var form = event.target;
    if (!form.matches(".cart-ajax-form")) {
      return;
    }

    event.preventDefault();
    var container = form.closest("[data-product-card], [data-cart-item]");
    var isCartPage = container.matches("[data-cart-item]");
    var errorBox = container.querySelector(".cart-error");
    var button = form.querySelector("button");
    button.disabled = true;
    if (errorBox) {
      errorBox.hidden = true;
    }

    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "Accept": "application/json"
      }
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok) {
            throw new Error(data.message);
          }
          return data;
        });
      })
      .then(function (data) {
        updateCartCount(data.cart_count);
        if (isCartPage) {
          updateCartPage(container, data);
          if (data.quantity === 0 && data.removed) {
            return;
          }
        } else {
          renderControls(container, data.quantity, data.stock);
        }
      })
      .catch(function (error) {
        if (errorBox) {
          errorBox.textContent = error.message;
          errorBox.hidden = false;
        }
        button.disabled = false;
      });
  });

  window.addEventListener("pageshow", function (event) {
    if (event.persisted) {
      window.location.reload();
    }
  });
})();

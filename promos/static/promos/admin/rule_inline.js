(function () {
  function toggleRuleRow(row) {
    const kindEl = row.querySelector('select[name$="-kind"]');
    if (!kindEl) return;

    const kind = kindEl.value;

    const map = {
      category_in: ["categories"],
      brand_in: ["brands"],
      product_in: ["products"],
      variant_in: ["variants"],
      cart_min_total: ["threshold"],
      qty_at_least: ["qty"],
    };

    const active = new Set(map[kind] || []);

    ["categories","brands","products","variants","threshold","qty"].forEach((name) => {
      const cell = row.querySelector(".field-" + name);
      if (!cell) return;
      cell.style.display = active.has(name) ? "" : "none";
    });
  }

  function init() {
    document.querySelectorAll("tr.form-row").forEach((row) => toggleRuleRow(row));

    document.addEventListener("change", function (e) {
      if (e.target && e.target.matches('select[name$="-kind"]')) {
        const row = e.target.closest("tr.form-row");
        if (row) toggleRuleRow(row);
      }
    });

    // وقتی inline جدید اضافه میشه
    document.body.addEventListener("formset:added", function (e) {
      const row = e.target;
      if (row && row.matches("tr.form-row")) toggleRuleRow(row);
    });
  }

  window.addEventListener("load", init);
})();

(function () {
  function toggleBannerFilter() {
    const kind = document.getElementById("id_filter_kind");
    if (!kind) return;

    const value = kind.value;

    const all = ["filter_categories", "filter_brands", "filter_products", "filter_variants"];
    const map = {
      category_in: ["filter_categories"],
      brand_in: ["filter_brands"],
      product_in: ["filter_products"],
      variant_in: ["filter_variants"],
    };
    const active = new Set(map[value] || []);

    all.forEach((name) => {
      const row = document.querySelector(".form-row.field-" + name) || document.querySelector(".form-row.field-" + name.replace("filter_", ""));
      const wrap = document.querySelector(".form-row.field-" + name);
      const el = document.querySelector("#id_" + name);
      const container = (wrap || (el ? el.closest(".form-row") : null));
      if (!container) return;
      container.style.display = active.has(name) ? "" : "none";
    });
  }

  window.addEventListener("load", function () {
    toggleBannerFilter();
    const kind = document.getElementById("id_filter_kind");
    if (kind) kind.addEventListener("change", toggleBannerFilter);
  });
})();

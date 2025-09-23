// static/products/js/pav-inline.js
(function ($) {
  "use strict";

  if (window.__PAV_INLINE_BOUND__) return;
  window.__PAV_INLINE_BOUND__ = true;

  var CHOICES_URL = window._pavChoicesURL || "/admin/products/product/attribute-choices/";

  function toStrArr(v){ if (!v) return []; if (Array.isArray(v)) return v.map(String); return [String(v)]; }

  function setKindVisibility($row, kind) {
    var $tdSingle = $row.find("td.field-value_choice");
    var $tdMulti  = $row.find("td.field-values_multi");

    if (kind === "choice") {
      $tdSingle.show();
      $tdMulti.hide().find("select").val([]);   // خالیِ چندتایی
    } else if (kind === "multi") {
      $tdMulti.show();
      $tdSingle.hide().find("select").val("");  // خالیِ تکی
    } else {
      $tdSingle.hide().find("select").val("");
      $tdMulti.hide().find("select").val([]);
    }
  }

  function applyInitialIfEmpty($single, $multi) {
    if ($single.length && !$single.val()) {
      var initSingle = $single.attr("data-initial") || "";
      if (initSingle && $single.find('option[value="'+initSingle+'"]').length) {
        $single.val(initSingle);
      }
    }
    if ($multi.length) {
      var cur = toStrArr($multi.val());
      if (!cur.length) {
        var initMulti = ($multi.attr("data-initial") || "")
                        .split(",").filter(Boolean);
        if (initMulti.length) {
          $multi.val(initMulti);
        }
      }
    }
    // یک‌بارمصرف
    $single.removeAttr("data-initial");
    $multi.removeAttr("data-initial");
  }

  // preserve=true یعنی مقدار فعلیِ DOM را پس از پرکردن دوباره، نگه‌دار
  function fillChoices($row, attrId, preserve) {
    var $single = $row.find('select[name$="-value_choice"]');
    var $multi  = $row.find('select[name$="-values_multi"]');

    var prevSingle = $single.length ? String($single.val() || "") : "";
    var prevMulti  = $multi.length ? toStrArr($multi.val()) : [];

    if ($single.length) $single.empty().append($('<option value="">---------</option>'));
    if ($multi.length)  $multi.empty();

    if (!attrId) { setKindVisibility($row, null); return; }

    var token = Date.now() + Math.random().toString(36).slice(2);
    $row.data("pavToken", token);

    $.getJSON(CHOICES_URL, { attr: attrId }).done(function (resp) {
      if ($row.data("pavToken") !== token) return;

      var items = (resp && resp.data) || [];
      var kind  = (resp && resp.kind) || null;

      items.forEach(function (it) {
        var v = String(it.id), t = it.label;
        if ($single.length) $single.append($("<option>").val(v).text(t));
        if ($multi.length)  $multi.append($("<option>").val(v).text(t));
      });

      if (preserve) {
        if ($single.length && prevSingle && $single.find('option[value="'+prevSingle+'"]').length) {
          $single.val(prevSingle);
        }
        if ($multi.length && prevMulti.length) {
          $multi.val(prevMulti);
        }
      }

      // اگر هنوز خالی‌اند، از data-initial بخوان
      applyInitialIfEmpty($single, $multi);

      setKindVisibility($row, kind);
    });
  }

  function initRow($row) {
    var $attr = $row.find('select[name$="-attribute"]');
    if (!$attr.length) return;

    var attrId = $attr.val();
    var hasSingleChoices = $row.find('td.field-value_choice select option').length > 1;
    var hasMultiChoices  = $row.find('td.field-values_multi  select option').length > 0;

    if (attrId && (hasSingleChoices || hasMultiChoices)) {
      // اگر سرور از قبل options را رندر کرده، فقط مطمئن شو مقدارهای initial/انتخاب‌شده از دست نرود
      applyInitialIfEmpty(
        $row.find('td.field-value_choice select'),
        $row.find('td.field-values_multi  select')
      );
      // ولی برای دانستن kind، یکبار AJAX می‌زنیم (بدون از دست دادن انتخاب‌ها)
      fillChoices($row, attrId, true);
    } else if (attrId) {
      fillChoices($row, attrId, true);
    } else {
      setKindVisibility($row, null);
    }
  }

  function wire() {
    // تغییر attribute توسط کاربر
    $(document).off("change.pav").on("change.pav",
      'select[name$="-attribute"]',
      function () {
        var $row = $(this).closest("tr.form-row");
        fillChoices($row, $(this).val(), false); // روی تغییر دستی، preserve لازم نیست
      });

    // بارگذاری اولیه (صفحه‌ی ویرایش)
    $('tr.form-row').each(function(){ initRow($(this)); });

    // ردیف‌های جدیدی که با «+» اضافه می‌شوند
    $(document).off("formset:added.pav").on("formset:added.pav", function (event, $row) {
      initRow($row);
    });
  }

  $(wire);
})(django.jQuery);

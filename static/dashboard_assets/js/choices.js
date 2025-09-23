(function () {
  "use strict";

  /* default multi select */
  const secondElement = new Choices('#choices-multiple-default', { allowSearch: false }).setValue(['گزینه 2', 'گزینه 3']);

  /* multi select with remove button */
  const multipleCancelButton = new Choices(
    '#choices-multiple-remove-button',
    {
      allowHTML: true,
      removeItemButton: true,
    }
  );

  /* multi select with option groups */
  const multipleDefault = new Choices(
    document.getElementById('choices-multiple-groups'),
    { allowHTML: true }
  );

  /* email address only */
  var textEmailFilter = new Choices('#choices-text-email-filter', {
    allowHTML: true,
    editItems: true,
    addItemFilter: function (value) {
      if (!value) {
        return false;
      }
      const regex = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
      const expression = new RegExp(regex.source, 'i');
      return expression.test(value);
    },
  }).setValue(['abc@hotmail.com']);

  /* passing through values */
  var textPresetVal = new Choices('#choices-text-preset-values', {
    allowHTML: true,
    items: [
      'یک',
      {
        value: 'two',
        label: 'دو',
        customProperties: {
          description: 'Numbers are infinite',
        },
      },
    ],
  });

  /* options added via config with no search */
  var singleNoSearch = new Choices('#choices-single-no-search', {
    allowHTML: true,
    searchEnabled: false,
    removeItemButton: true,
    choices: [
      { value: 'One', label: 'یک' },
      { value: 'Two', label: 'دو' },
      { value: 'Three', label: 'سه' },
    ],
  }).setChoices(
    [
      { value: 'Four', label: 'چهار' },
      { value: 'Five', label: 'پنج' },
      { value: 'Six', label: 'شش', selected: true },
    ],
    'value',
    'label',
    false
  );

  /* passing unique values */
  var textUniqueVals = new Choices('#choices-text-unique-values', {
    allowHTML: true,
    paste: false,
    duplicateItemsAllowed: false,
    editItems: true,
  });

})();
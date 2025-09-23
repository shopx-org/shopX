(function () {
    "use strict";


    /* multi select with remove button */
    const multipleCancelButton = new Choices(
        '#choices-multiple-remove-button',
        {
            allowHTML: true,
            removeItemButton: true,
        }
    );

    /* draggable js */
    dragula([document.getElementById('todo-drag')],{
        moves: function (el, container, handle) {
            return handle.classList.contains('todo-handle');
          }
    });

})();
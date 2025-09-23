(function () {
    "use strict";

    var tree = new TreeView([
        {
            name: 'لیست', children: [
                { name: 'نام شرکت', children: [] },
                { name: 'کارمندان', children: [] },
                { name: 'منابع انسانی', children: [] }
            ]
        },
        {
            name: 'شرکت ایکس', expanded: true, children: [
                { name: 'نام شرکت', children: [] },
                {
                    name: 'کارمندان', expanded: true, children: [
                        { name: 'نام شرکت-۱', children: [] },
                        {
                            name: 'کارمندان-۱', expanded: true, children: [
                                { name: 'نام شرکت-۲', children: [] },
                                { name: 'کارمندان-۲', children: [] },
                                { name: 'منابع انسانی-۲', children: [] }
                            ]
                        },
                        { name: 'منابع انسانی', children: [] }
                    ]
                },
                { name: 'کارمندان', children: [] }
            ]
        },
        {
            name: 'لیست۲', expanded: false, children: [
                { name: 'نام شرکت', children: [] },
                {
                    name: 'کارمندان', children: [
                        { name: 'نام شرکت', children: [] },
                        {
                            name: 'کارمندان', children: [
                                { name: 'نام شرکت', children: [] },
                                { name: 'کارمندان', children: [] },
                                { name: 'منابع انسانی', children: [] }
                            ]
                        },
                        { name: 'منابع انسانی', children: [] }
                    ]
                }
            ]
        },
        { name: 'لیست۳', children: [] },
    ], 'tree');
})();
// Main Js File
$(document).ready(function () {
    'use strict';

    owlCarousels();
    quantityInputs();

    // Header Search Toggle

    var $searchWrapper = $('.header-search-wrapper'),
        $body = $('body'),
        $searchToggle = $('.search-toggle');

    $searchToggle.on('click', function (e) {
        $searchWrapper.toggleClass('show');
        $(this).toggleClass('active');
        $searchWrapper.find('input').focus();
        e.preventDefault();
    });

    $body.on('click', function (e) {
        if ($searchWrapper.hasClass('show')) {
            $searchWrapper.removeClass('show');
            $searchToggle.removeClass('active');
            $body.removeClass('is-search-active');
        }
    });

    $('.header-search').on('click', function (e) {
        e.stopPropagation();
    });

    // Ckeckout2
    $('.step-next').on('click', function () {
        var nextId = $(this).closest('.tab-pane').next().attr('id');
        $('[href="#' + nextId + '"]').tab('show');
        return false;
    });

    // LookBook
    $('.lookbook-dot').on('click', function () {
        if ($(this).hasClass('istatic') && $(this).find('.dot-showbox').hasClass('save')) {
            $(this).find('.dot-showbox').removeClass('active')
        }
        if ($(this).find('.dot-showbox').hasClass('active')) {
            $(this).removeClass('show-menu');
            $(this).find('.dot-showbox').removeClass('active');
        } else {
            $('.dot-showbox').removeClass('active');
            $('.dot-showbox').removeClass('save');
            $('.lookbook-dot').removeClass('istatic');
            $(this).find('.dot-showbox').addClass('active');
            $('.lookbook-dot').removeClass('show-menu');
            $(this).addClass('show-menu');
        }
    });

    $('.dot-showbox').on('click', function () {
        $(this).addClass('save');
        $('.lookbook-dot').addClass('istatic');
    });

    $('.close-lookbook').on('click', function() {
        $('.dot-showbox').removeClass('active');
        $('.lookbook-dot').removeClass('show-menu');
        return false;
    });


    // Sticky header 
    var catDropdown = $('.category-dropdown'),
        catInitVal = catDropdown.data('visible');

    if ($('.sticky-header').length && $(window).width() >= 992) {
        var sticky = new Waypoint.Sticky({
            element: $('.sticky-header')[0],
            stuckClass: 'fixed',
            offset: -300,
            handler: function (direction) {
                // Show category dropdown
                if (catInitVal && direction == 'up') {
                    catDropdown.addClass('show').find('.dropdown-menu').addClass('show');
                    catDropdown.find('.dropdown-toggle').attr('aria-expanded', 'true');
                    return false;
                }

                // Hide category dropdown on fixed header
                if (catDropdown.hasClass('show')) {
                    catDropdown.removeClass('show').find('.dropdown-menu').removeClass('show');
                    catDropdown.find('.dropdown-toggle').attr('aria-expanded', 'false');
                }
            }
        });
    }

    // Menu init with superfish plugin
    if ($.fn.superfish) {
        $('.menu, .menu-vertical').superfish({
            popUpSelector: 'ul, .megamenu',
            hoverClass: 'show',
            delay: 0,
            speed: 80,
            speedOut: 80,
            autoArrows: true
        });
    }

    // Mobile Menu Toggle - Show & Hide
    $('.mobile-menu-toggler').on('click', function (e) {
        $body.toggleClass('mmenu-active');
        $(this).toggleClass('active');
        e.preventDefault();
    });

    $('.mobile-menu-overlay, .mobile-menu-close').on('click', function (e) {
        $body.removeClass('mmenu-active');
        $('.menu-toggler').removeClass('active');
        e.preventDefault();
    });

    // Add Mobile menu icon arrows to items with children
    $('.mobile-menu').find('li').each(function () {
        var $this = $(this);

        if ($this.find('ul').length) {
            $('<span/>', {
                'class': 'mmenu-btn'
            }).appendTo($this.children('a'));
        }
    });

    // Mobile Menu toggle children menu
    $('.mmenu-btn').on('click', function (e) {
        var $parent = $(this).closest('li'),
            $targetUl = $parent.find('ul').eq(0);

        if (!$parent.hasClass('open')) {
            $targetUl.slideDown(300, function () {
                $parent.addClass('open');
            });
        } else {
            $targetUl.slideUp(300, function () {
                $parent.removeClass('open');
            });
        }

        e.stopPropagation();
        e.preventDefault();
    });

    // Sidebar Filter - Show & Hide
    var $sidebarToggler = $('.sidebar-toggler');
    $sidebarToggler.on('click', function (e) {
        $body.toggleClass('sidebar-filter-active');
        $(this).toggleClass('active');
        e.preventDefault();
    });

    $('.sidebar-filter-overlay').on('click', function (e) {
        $body.removeClass('sidebar-filter-active');
        $sidebarToggler.removeClass('active');
        e.preventDefault();
    });

    // Clear All checkbox/remove filters in sidebar filter
    $('.sidebar-filter-clear').on('click', function (e) {
        $('.sidebar-shop').find('input').prop('checked', false);

        e.preventDefault();
    });

    // Popup - Iframe Video - Map etc.
    if ($.fn.magnificPopup) {
        $('.btn-iframe').magnificPopup({
            type: 'iframe',
            removalDelay: 600,
            preloader: false,
            fixedContentPos: false,
            closeBtnInside: false
        });
    }

    // Product hover
    if ($.fn.hoverIntent) {
        $('.product-3').hoverIntent(function () {
            var $this = $(this),
                animDiff = ($this.outerHeight() - ($this.find('.product-body').outerHeight() + $this.find('.product-media').outerHeight())),
                animDistance = ($this.find('.product-footer').outerHeight() - animDiff);

            $this.find('.product-footer').css({
                'visibility': 'visible',
                'transform': 'translateY(0)'
            });
            $this.find('.product-body').css('transform', 'translateY(' + -animDistance + 'px)');

        }, function () {
            var $this = $(this);

            $this.find('.product-footer').css({
                'visibility': 'hidden',
                'transform': 'translateY(100%)'
            });
            $this.find('.product-body').css('transform', 'translateY(0)');
        });
    }

    // Slider For category pages / filter price
    if (typeof noUiSlider === 'object') {
        var priceSlider = document.getElementById('price-slider');

        // Check if #price-slider elem is exists if not return
        // to prevent error logs
        if (priceSlider == null) return;

        noUiSlider.create(priceSlider, {
            start: [100000, 750000],
            connect: true,
            step: 50,
            margin: 200,
            range: {
                'min': 1000,
                'max': 1000000
            },
            tooltips: true,
            format: wNumb({
                decimals: 0,
                suffix: 'تومان'
            })
        });

        // Update Price Range
        priceSlider.noUiSlider.on('update', function (values, handle) {
            $('#filter-price-range').text(values.join(' - '));
        });
    }

    // Product countdown
    if ($.fn.countdown) {
        $('.product-countdown').each(function () {
            var $this = $(this),
                untilDate = $this.data('until'),
                compact = $this.data('compact'),
                dateFormat = (!$this.data('format')) ? 'DHMS' : $this.data('format'),
                newLabels = (!$this.data('labels-short')) ? ['سال', 'ماه', 'هفته', 'روز', 'ساعت', 'دقیقه', 'ثانیه'] : ['سال', 'ماه', 'هفته', 'روز', 'ساعت', 'دقیقه', 'ثانیه'],
                newLabels1 = (!$this.data('labels-short')) ? ['سال', 'ماه', 'هفته', 'روز', 'ساعت', 'دقیقه', 'ثانیه'] : ['سال', 'ماه', 'هفته', 'روز', 'ساعت', 'دقیقه', 'ثانیه'];

            var newDate;

            // Split and created again for ie and edge 
            if (!$this.data('relative')) {
                var untilDateArr = untilDate.split(", "), // data-until 2019, 10, 8 - yy,mm,dd
                    newDate = new Date(untilDateArr[0], untilDateArr[1] - 1, untilDateArr[2]);
            } else {
                newDate = untilDate;
            }

            $this.countdown({
                until: newDate,
                format: dateFormat,
                padZeroes: true,
                compact: compact,
                compactLabels: ['y', 'm', 'w', ' روز,'],
                timeSeparator: ' : ',
                labels: newLabels,
                labels1: newLabels1

            });
        });

        // Pause
        // $('.product-countdown').countdown('pause');
    }

    // Quantity Input - Cart page - Product Details pages
    function quantityInputs() {
        if ($.fn.inputSpinner) {
            $("input[type='number']").inputSpinner({
                decrementButton: '<i class="icon-minus"></i>',
                incrementButton: '<i class="icon-plus"></i>',
                groupClass: 'input-spinner',
                buttonsClass: 'btn-spinner',
                buttonsWidth: '26px'
            });
        }
    }

    // Sticky Content - Sidebar - Social Icons etc..
    // Wrap elements with <div class="sticky-content"></div> if you want to make it sticky
    if ($.fn.stick_in_parent && $(window).width() >= 992) {
        $('.sticky-content').stick_in_parent({
            offset_top: 80,
            inner_scrolling: false
        });
    }

    function owlCarousels($wrap, options) {
        if ($.fn.owlCarousel) {
            var owlSettings = {
                items: 1,
                loop: true,
                margin: 0,
                responsiveClass: true,
                nav: true,
                navText: ['<i class="icon-angle-right">', '<i class="icon-angle-left">'],
                dots: true,
                smartSpeed: 400,
                autoplay: false,
                autoplayTimeout: 15000
            };
            if (typeof $wrap == 'undefined') {
                $wrap = $('body');
            }
            if (options) {
                owlSettings = $.extend({}, owlSettings, options);
            }

            // Init all carousel
            $wrap.find('[data-toggle="owl"]').each(function () {
                var $this = $(this),
                    newOwlSettings = $.extend({}, owlSettings, $this.data('owl-options'));

                $this.owlCarousel(newOwlSettings);

                $('body').addClass('loaded');
            });
        }
    }

    // Product Image Zoom plugin - product pages
    if ($.fn.elevateZoom) {
        $('#product-zoom').elevateZoom({
            gallery: 'product-zoom-gallery',
            galleryActiveClass: 'active',
            zoomType: "inner",
            cursor: "crosshair",
            zoomWindowFadeIn: 400,
            zoomWindowFadeOut: 400,
            responsive: true
        });

        // On click change thumbs active item
        $('.product-gallery-item').on('click', function (e) {
            $('#product-zoom-gallery').find('a').removeClass('active');
            $(this).addClass('active');

            e.preventDefault();
        });

        var ez = $('#product-zoom').data('elevateZoom');

        // Open popup - product images
        $('#btn-product-gallery').on('click', function (e) {
            if ($.fn.magnificPopup) {
                $.magnificPopup.open({
                    items: ez.getGalleryList(),
                    type: 'image',
                    gallery: {
                        enabled: true
                    },
                    fixedContentPos: false,
                    removalDelay: 600,
                    closeBtnInside: false
                }, 0);

                e.preventDefault();
            }
        });
    }

    // Product Gallery - product-gallery.html 
    if ($.fn.owlCarousel && $.fn.elevateZoom) {
        var owlProductGallery = $('.product-gallery-carousel');

        owlProductGallery.on('initialized.owl.carousel', function () {
            owlProductGallery.find('.active img').elevateZoom({
                zoomType: "inner",
                cursor: "crosshair",
                zoomWindowFadeIn: 400,
                zoomWindowFadeOut: 400,
                responsive: true
            });
        });

        owlProductGallery.owlCarousel({
            rtl:true,
            loop: false,
            margin: 0,
            responsiveClass: true,
            nav: true,
            navText: ['<i class="icon-angle-right">', '<i class="icon-angle-left">'],
            dots: false,
            smartSpeed: 400,
            autoplay: false,
            autoplayTimeout: 15000,
            responsive: {
                0: {
                    items: 1
                },
                560: {
                    items: 2
                },
                992: {
                    items: 3
                },
                1200: {
                    items: 3
                }
            }
        });

        owlProductGallery.on('change.owl.carousel', function () {
            $('.zoomContainer').remove();
        });

        owlProductGallery.on('translated.owl.carousel', function () {
            owlProductGallery.find('.active img').elevateZoom({
                zoomType: "inner",
                cursor: "crosshair",
                zoomWindowFadeIn: 400,
                zoomWindowFadeOut: 400,
                responsive: true
            });
        });
    }

    // Product Gallery Separeted- product-sticky.html 
    if ($.fn.elevateZoom) {
        $('.product-separated-item').find('img').elevateZoom({
            zoomType: "inner",
            cursor: "crosshair",
            zoomWindowFadeIn: 400,
            zoomWindowFadeOut: 400,
            responsive: true
        });

        // Create Array for gallery popup
        var galleryArr = [];
        $('.product-gallery-separated').find('img').each(function () {
            var $this = $(this),
                imgSrc = $this.attr('src'),
                imgTitle = $this.attr('alt'),
                obj = {
                    'src': imgSrc,
                    'title': imgTitle
                };

            galleryArr.push(obj);
        })

        $('#btn-separated-gallery').on('click', function (e) {
            if ($.fn.magnificPopup) {
                $.magnificPopup.open({
                    items: galleryArr,
                    type: 'image',
                    gallery: {
                        enabled: true
                    },
                    fixedContentPos: false,
                    removalDelay: 600,
                    closeBtnInside: false
                }, 0);

                e.preventDefault();
            }
        });
    }

    // Checkout discount input - toggle label if input is empty etc...
    $('#checkout-discount-input').on('focus', function () {
        // Hide label on focus
        $(this).parent('form').find('label').css('opacity', 0);
    }).on('blur', function () {
        // Check if input is empty / toggle label
        var $this = $(this);

        if ($this.val().length !== 0) {
            $this.parent('form').find('label').css('opacity', 0);
        } else {
            $this.parent('form').find('label').css('opacity', 1);
        }
    });

    // Dashboard Page Tab Trigger
    $('.tab-trigger-link').on('click', function (e) {
        var targetHref = $(this).attr('href');

        $('.nav-dashboard').find('a[href="' + targetHref + '"]').trigger('click');

        e.preventDefault();
    });

    $('.step-next').on('click', function () {
        var nextId = $(this).closest('.tab-pane').next().attr('id');
        $('[href="#' + nextId + '"]').tab('show');
        return false;
    });
    $('a[data-toggle="tab"]').on('shown.bs.tab', function (e) {
        var step = $(e.target).data('step');
        var percent = parseInt(step) / 4 * 100;
        $('.progress-bar').css({
            width: percent + '%'
        });
        e.relatedTarget;
    });
    $('.step-next-accordion').on('click', function () {
        var $nextPanel = $(this).closest('.panel').next('.panel');
        if ($nextPanel) $nextPanel.find('.panel-title > a').trigger('click');
        return false;
    });

    // Masonry / Grid layout fnction
    var layoutInit = function (container, selector, space) {
        $(container).each(function () {
            var $this = $(this);

            $this.isotope({
                itemSelector: selector,
                layoutMode: ($this.data('layout') ? $this.data('layout') : 'masonry'),
                masonry: {
                    columnWidth: space
                }
            });
        });
    }

    var isotopeFilter = function (filterNav, container) {
        $(filterNav).find('a').on('click', function (e) {
            var $this = $(this),
                filter = $this.attr('data-filter');

            // Remove active class
            $(filterNav).find('.active').removeClass('active');

            // Init filter
            $(container).isotope({
                filter: filter,
                transitionDuration: '0.7s'
            });

            // Add active class
            $this.closest('li').addClass('active');
            e.preventDefault();
        });
    }

    /* Masonry / Grid Layout & Isotope Filter for blog/portfolio etc... */
    if (typeof imagesLoaded === 'function' && $.fn.isotope) {
        // Portfolio
        $('.portfolio-container').imagesLoaded(function () {
            // Portfolio Grid/Masonry
            layoutInit('.portfolio-container', '.portfolio-item'); // container - selector
            // Portfolio Filter
            isotopeFilter('.portfolio-filter', '.portfolio-container'); //filterNav - .container
        });

        // Blog
        $('.entry-container').imagesLoaded(function () {
            // Blog Grid/Masonry
            layoutInit('.entry-container', '.entry-item'); // container - selector
            // Blog Filter
            isotopeFilter('.entry-filter', '.entry-container'); //filterNav - .container
        });

        // Product masonry product-masonry.html
        $('.product-gallery-masonry').imagesLoaded(function () {
            // Products Grid/Masonry
            layoutInit('.product-gallery-masonry', '.product-gallery-item'); // container - selector
        });

        // Products - Demo 11
        $('.products-container').imagesLoaded(function () {
            // Products Grid/Masonry
            layoutInit('.products-container', '.product-item'); // container - selector
            // Product Filter
            isotopeFilter('.product-filter', '.products-container'); //filterNav - .container
        });

        layoutInit('.grid', '.grid-item', '.grid-space');
    }

    // Count
    var $countItem = $('.count');
    if ($.fn.countTo) {
        if ($.fn.waypoint) {
            $countItem.waypoint(function () {
                $(this.element).countTo();
            }, {
                offset: '90%',
                triggerOnce: true
            });
        } else {
            $countItem.countTo();
        }
    } else {
        // fallback
        // Get the data-to value and add it to element
        $countItem.each(function () {
            var $this = $(this),
                countValue = $this.data('to');
            $this.text(countValue);
        });
    }

    // Scroll To button
    var $scrollTo = $('.scroll-to');
    // If button scroll elements exists
    if ($scrollTo.length) {
        // Scroll to - Animate scroll
        $scrollTo.on('click', function (e) {
            var target = $(this).attr('href'),
                $target = $(target);
            if ($target.length) {
                // Add offset for sticky menu
                var scrolloffset = ($(window).width() >= 992) ? ($target.offset().top - 52) : $target.offset().top
                $('html, body').animate({
                    'scrollTop': scrolloffset
                }, 600);
                e.preventDefault();
            }
        });
    }

    // Review tab/collapse show + scroll to tab
    $('#review-link').on('click', function (e) {
        var target = $(this).attr('href'),
            $target = $(target);

        if ($('#product-accordion-review').length) {
            $('#product-accordion-review').collapse('show');
        }

        if ($target.length) {
            // Add offset for sticky menu
            var scrolloffset = ($(window).width() >= 992) ? ($target.offset().top - 72) : ($target.offset().top - 10)
            $('html, body').animate({
                'scrollTop': scrolloffset
            }, 600);

            $target.tab('show');
        }

        e.preventDefault();
    });

    // Scroll Top Button - Show
    var $scrollTop = $('#scroll-top');

    $(window).on('load scroll', function () {
        if ($(window).scrollTop() >= 400) {
            $scrollTop.addClass('show');
        } else {
            $scrollTop.removeClass('show');
        }
    });

    // On click animate to top
    $scrollTop.on('click', function (e) {
        $('html, body').animate({
            'scrollTop': 0
        }, 800);
        e.preventDefault();
    });

    // Google Map api v3 - Map for contact pages
    if (document.getElementById("map") && typeof google === "object") {

        var content = '<address>' +
            '88 Pine St,<br>' +
            'New York, NY 10005, USA<br>' +
            '<a href="#" class="direction-link" target="_blank">Get Directions <i class="icon-angle-right"></i></a>' +
            '</address>';

        var latLong = new google.maps.LatLng(40.8127911, -73.9624553);

        var map = new google.maps.Map(document.getElementById('map'), {
            zoom: 14,
            center: latLong, // Map Center coordinates
            scrollwheel: false,
            mapTypeId: google.maps.MapTypeId.ROADMAP

        });

        var infowindow = new google.maps.InfoWindow({
            content: content,
            maxWidth: 360
        });

        var marker;
        marker = new google.maps.Marker({
            position: latLong,
            map: map,
            animation: google.maps.Animation.DROP
        });

        google.maps.event.addListener(marker, 'click', (function (marker) {
            return function () {
                infowindow.open(map, marker);
            }
        })(marker));
    }

    var $viewAll = $('.view-all-demos');
    $viewAll.on('click', function (e) {
        e.preventDefault();
        $('.demo-item.hidden').addClass('show');
        $(this).addClass('disabled-hidden');
    })

    var $megamenu = $('.megamenu-container .sf-with-ul');
    $megamenu.hover(function () {
        $('.demo-item.show').addClass('hidden');
        $('.demo-item.show').removeClass('show');
        $viewAll.removeClass('disabled-hidden');
    });

    // Product quickView popup
    $('.btn-quickview').on('click', function (e) {
        var ajaxUrl = $(this).attr('href');
        if ($.fn.magnificPopup) {
            setTimeout(function () {
                $.magnificPopup.open({
                    type: 'ajax',
                    mainClass: "mfp-ajax-product",
                    tLoading: '',
                    preloader: false,
                    removalDelay: 350,
                    items: {
                        src: ajaxUrl
                    },
                    callbacks: {
                        ajaxContentAdded: function () {
                            owlCarousels($('.quickView-content'), {
                                onTranslate: function (e) {
                                    var $this = $(e.target),
                                        currentIndex = ($this.data('owl.carousel').current() + e.item.count - Math.ceil(e.item.count / 2)) % e.item.count;
                                    $('.quickView-content .carousel-dot').eq(currentIndex).addClass('active').siblings().removeClass('active');
                                }
                            });
                            quantityInputs();
                        },
                        open: function () {
                            $('body').css('overflow-x', 'hidden');
                            $('.sticky-header.fixed').css('padding-right', '1.7rem');
                        },
                        close: function () {
                            $('body').css('overflow-x', 'hidden');
                            $('.sticky-header.fixed').css('padding-right', '0');
                        }
                    },

                    ajax: {
                        tError: '',
                    }
                }, 0);
            }, 500);

            e.preventDefault();
        }
    });
    $('body').on('click', '.carousel-dot', function () {
        $(this).siblings().removeClass('active');
        $(this).addClass('active');
    });

    $('body').on('click', '.btn-fullscreen', function (e) {
        var galleryArr = [];
        $(this).parents('.owl-stage-outer').find('.owl-item:not(.cloned)').each(function () {
            var $this = $(this).find('img'),
                imgSrc = $this.attr('src'),
                imgTitle = $this.attr('alt'),
                obj = {
                    'src': imgSrc,
                    'title': imgTitle
                };
            galleryArr.push(obj);
        });

        var ajaxUrl = $(this).attr('href');

        var mpInstance = $.magnificPopup.instance;
        if (mpInstance.isOpen)
            mpInstance.close();

        setTimeout(function () {
            $.magnificPopup.open({
                type: 'ajax',
                mainClass: "mfp-ajax-product",
                tLoading: '',
                preloader: false,
                removalDelay: 350,
                items: {
                    src: ajaxUrl
                },
                callbacks: {
                    ajaxContentAdded: function () {
                        owlCarousels($('.quickView-content'), {
                            onTranslate: function (e) {
                                var $this = $(e.target),
                                    currentIndex = ($this.data('owl.carousel').current() + e.item.count - Math.ceil(e.item.count / 2)) % e.item.count;
                                $('.quickView-content .carousel-dot').eq(currentIndex).addClass('active').siblings().removeClass('active');
                                $('.curidx').html(currentIndex + 1);
                            }
                        });
                        quantityInputs();
                    },
                    open: function () {
                        $('body').css('overflow-x', 'hidden');
                        $('.sticky-header.fixed').css('padding-right', '1.7rem');
                    },
                    close: function () {
                        $('body').css('overflow-x', 'hidden');
                        $('.sticky-header.fixed').css('padding-right', '0');
                    }
                },

                ajax: {
                    tError: '',
                }
            }, 0);
        }, 500);

        e.preventDefault();
    });

    if (document.getElementById('newsletter-popup-form')) {
        setTimeout(function () {
            var mpInstance = $.magnificPopup.instance;
            if (mpInstance.isOpen) {
                mpInstance.close();
            }

            setTimeout(function () {
                $.magnificPopup.open({
                    items: {
                        src: '#newsletter-popup-form'
                    },
                    type: 'inline',
                    removalDelay: 350,
                    callbacks: {
                        open: function () {
                            $('body').css('overflow-x', 'hidden');
                            $('.sticky-header.fixed').css('padding-right', '1.7rem');
                        },
                        close: function () {
                            $('body').css('overflow-x', 'hidden');
                            $('.sticky-header.fixed').css('padding-right', '0');
                        }
                    }
                });
            }, 500)
        }, 900)
    }

    $('#printinvoice').click(function () {
        Popup($('.invoice-popup')[0].outerHTML);

        function Popup(data) {
            window.print();
            return true;
        }
    });
});

document.addEventListener('click', function (e) {
  const btn = e.target.closest('.qty-btn');
  if (!btn) return;

  const box = btn.closest('.qty');
  const input = box.querySelector('input[type="number"]');
  const min = parseInt(input.min || '1', 10);
  const step = parseInt(btn.dataset.step || '0', 10);

  let v = parseInt(input.value || '1', 10);
  v = isNaN(v) ? min : v + step;
  if (v < min) v = min;

  input.value = v;
});

    // ---- Cart header summary (badge + total) ----
    (function () {
        var $badge = $('.cart-dropdown .cart-count');
        var $total = $('.cart-dropdown .cart-total-price');

        if (!$badge.length && !$total.length) {
            return;
        }

        $.ajax({
            url: '/cart/api/header-summary/',
            method: 'GET',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).done(function (data) {
            if (!data || !data.ok || !data.summary) return;

            var sum = data.summary;

            // تعداد آیتم‌ها
            if ($badge.length) {
                $badge.text(sum.items_count || 0);
            }

            // مبلغ کل پرداختی
            if ($total.length) {
                var formatter = new Intl.NumberFormat('fa-IR');
                var t = sum.total || 0;
                $total.text(formatter.format(t) + ' تومان');
            }
        }).fail(function () {
            // در صورت خطا چیزی تغییر نده
        });
    })();

    // ---- Cart header summary (badge + total) ----
    (function () {
        var $badge = $('.cart-dropdown .cart-count');
        var $total = $('.cart-dropdown .cart-total-price');

        if (!$badge.length && !$total.length) {
            return;
        }

        $.ajax({
            url: '/cart/api/header-summary/',
            method: 'GET',
            headers: {'X-Requested-With': 'XMLHttpRequest'}
        }).done(function (data) {
            if (!data || !data.ok || !data.summary) return;

            var sum = data.summary;

            // تعداد آیتم‌ها
            if ($badge.length) {
                $badge.text(sum.items_count || 0);
            }

            // مبلغ کل پرداختی
            if ($total.length) {
                var formatter = new Intl.NumberFormat('fa-IR');
                var t = sum.total || 0;
                $total.text(formatter.format(t) + ' تومان');
            }
        }).fail(function () {
            // در صورت خطا چیزی تغییر نده
        });
    })();
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
        const cookies = document.cookie.split(";");
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) === (name + "=")) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener("DOMContentLoaded", function () {
    const methodInputs = document.querySelectorAll('input[name="shipping_method"]');
    const summaryBox = document.getElementById("summary");
    const shipLine = document.getElementById("s-shipline");
    const shipValue = document.getElementById("s-ship");
    const totalValue = document.getElementById("s-total");

    if (!methodInputs.length || !summaryBox || !shipLine || !shipValue || !totalValue) {
        return;
    }

    const csrftoken = getCookie("csrftoken");

    function formatToman(num) {
        // ساده: جداکننده هزار
        const n = parseInt(num || 0, 10);
        return n.toLocaleString("fa-IR") + " تومان";
    }

    function recalcTotal(shippingAmount) {
        const sub = parseInt(summaryBox.dataset.sub || "0", 10);
        const disc = parseInt(summaryBox.dataset.disc || "0", 10);
        const svc = parseInt(summaryBox.dataset.svc || "0", 10);
        const ship = parseInt(shippingAmount || "0", 10);

        const total = (sub - disc) + svc + ship;
        summaryBox.dataset.total = total;

        shipLine.style.display = ship > 0 ? "flex" : "none";
        shipValue.textContent = formatToman(ship);
        totalValue.textContent = formatToman(total);
    }

    function sendQuote(methodId) {
        if (!window.shippingQuoteURL) {
            return;
        }

        fetch(window.shippingQuoteURL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrftoken,
                "X-Requested-With": "XMLHttpRequest"
            },
            body: JSON.stringify({
                shipping_method_id: methodId
            })
        })
            .then(res => res.json())
            .then(data => {
                if (!data.ok) {
                    console.warn("Shipping quote error:", data.error);
                    recalcTotal(0);
                    return;
                }
                recalcTotal(data.shipping_amount);
            })
            .catch(err => {
                console.error("Shipping quote exception:", err);
                recalcTotal(0);
            });
    }

    methodInputs.forEach(input => {
        input.addEventListener("change", function () {
            const methodId = this.value;
            if (methodId) {
                sendQuote(methodId);
            }
        });

        // اگر از قبل یکی checked است، یک بار اول صفحه هم براش quote بگیر
        if (input.checked) {
            sendQuote(input.value);
        }
    });
});

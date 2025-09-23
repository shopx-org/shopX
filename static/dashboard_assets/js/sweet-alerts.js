(function () {
    'use strict';

    /* for basic sweet alert */
    document.getElementById('basic-alert').onclick = function () {
        Swal.fire('پیغام ساده')
    };
    document.getElementById('alert-text').onclick = function () {
        Swal.fire(
            'اینترنت؟',
            'آن چیز هنوز در اطراف است؟',
            'question'
        )
    }
    document.getElementById('alert-footer').onclick = function () {
        Swal.fire({
            icon: 'error',
            title: 'متاسفیم...',
            text: 'خطا!',
            footer: '<a href="javascript:void(0);">چرا من این مشکل را دارم؟</a>'
        })
    }
    document.getElementById('long-window').onclick = function () {
        Swal.fire({
            imageUrl: 'https://placeholder.pics/svg/300x1500',
            imageHeight: 1500,
            imageAlt: 'عکس'
        })
    }
    document.getElementById('alert-description').onclick = function () {
        Swal.fire({
            title: '<strong>HTML <u>نمونه</u></strong>',
            icon: 'info',
            html:
                '<b>متن بولد شده</b>, ' +
                '<a href="https://sweetalert2.github.io/" target="blank">لینک</a> ' +
                '',
            showCloseButton: true,
            showCancelButton: true,
            focusConfirm: false,
            confirmButtonText:
                '<i class="fe fe-thumbs-up"></i> تایید!',
            confirmButtonAriaLabel: 'تایید!',
            cancelButtonText:
                '<i class="fe fe-thumbs-down"></i>',
            cancelButtonAriaLabel: 'لغو'
        })
    }
    document.getElementById('three-buttons').onclick = function () {
        Swal.fire({
            title: 'از ذخیره اطلاعات اطمینان دارید؟',
            showDenyButton: true,
            showCancelButton: false,
            confirmButtonText: 'بله',
            denyButtonText: `خیر`,
        }).then((result) => {
            /* Read more about isConfirmed, isDenied below */
            if (result.isConfirmed) {
                Swal.fire('دخیره شد!', '', 'success')
            } else if (result.isDenied) {
                Swal.fire('لغو شد', '', 'info')
            }
        })
    }
    document.getElementById('alert-dialog').onclick = function () {
        Swal.fire({
            position: 'top-end',
            icon: 'success',
            title: 'اطلاعات با موفقیت ذخیره سازی شد',
            showConfirmButton: false,
            timer: 1500
        })
    }
    document.getElementById('alert-confirm').onclick = function () {
        Swal.fire({
            title: 'مطمئن هستید?',
            text: "شما نمی توانید این را برگردانید!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#3085d6',
            cancelButtonColor: '#d33',
            confirmButtonText: 'بله'
        }).then((result) => {
            if (result.isConfirmed) {
                Swal.fire(
                    'حذف شد!',
                    'عملیات موفق!',
                    'success'
                )
            }
        })
    }
    document.getElementById('alert-parameter').onclick = function () {
        const swalWithBootstrapButtons = Swal.mixin({
            customClass: {
                confirmButton: 'btn btn-success ms-2',
                cancelButton: 'btn btn-danger'
            },
            buttonsStyling: false
        })

        swalWithBootstrapButtons.fire({
            title: 'مطمئن هستید?',
            text: "شما نمی توانید این را برگردانید!",
            icon: 'warning',
            showCancelButton: true,
            confirmButtonText: 'بله',
            cancelButtonText: 'خیر',
            reverseButtons: true
        }).then((result) => {
            if (result.isConfirmed) {
                swalWithBootstrapButtons.fire(
                    'Deleted!',
                    'Your file has been deleted.',
                    'success'
                )
            } else if (
                /* Read more about handling dismissals below */
                result.dismiss === Swal.DismissReason.cancel
            ) {
                swalWithBootstrapButtons.fire(
                    'Cancelled',
                    'Your imaginary file is safe :)',
                    'error'
                )
            }
        })
    }
    document.getElementById('alert-image').onclick = function () {
        Swal.fire({
            title: 'لورم ایپسوم!',
            text: 'مدال همراه با عکس',
            imageUrl: 'assets/images/media/media-59.jpg',
            imageWidth: 400,
            imageHeight: 200,
            imageAlt: 'عکس',
        })
    }
    document.getElementById('alert-custom-bg').onclick = function () {
        Swal.fire({
            title: 'اندازه سفارشی',
            width: 600,
            padding: '3em',
            color: '#716add',
            background: 'url(assets/images/media/media-19.jpg)',
            backdrop: `
              rgba(0,0,0,0.3)
              url(assets/images/gif's/1.gif)
              left top
              no-repeat
            `
        })
    }
    document.getElementById('alert-auto-close').onclick = function () {
        let timerInterval
        Swal.fire({
            title: 'بستن خودکار',
            html: 'بستن بعد از  <b></b> میلی ثانیه.',
            timer: 2000,
            timerProgressBar: true,
            didOpen: () => {
                Swal.showLoading()
                const b = Swal.getHtmlContainer().querySelector('b')
                timerInterval = setInterval(() => {
                    b.textContent = Swal.getTimerLeft()
                }, 100)
            },
            willClose: () => {
                clearInterval(timerInterval)
            }
        }).then((result) => {
            /* Read more about handling dismissals below */
            if (result.dismiss === Swal.DismissReason.timer) {
                console.log('I was closed by the timer')
            }
        })
    }
    document.getElementById('alert-ajax').onclick = function () {
        Swal.fire({
            title: 'ارسال فرم',
            input: 'text',
            inputAttributes: {
                autocapitalize: 'off'
            },
            showCancelButton: true,
            confirmButtonText: 'بررسی',
            showLoaderOnConfirm: true,
            preConfirm: (login) => {
                return fetch(`https://jsonplaceholder.typicode.com/posts`)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(response.statusText)
                        }
                        return response.json()
                    })
                    .catch(error => {
                        Swal.showValidationMessage(
                            `Request failed: ${error}`
                        )
                    })
            },
            allowOutsideClick: () => !Swal.isLoading()
        }).then((result) => {
            if (result.isConfirmed) {
                Swal.fire({
                    title: `${result.value.login}'s avatar`,
                    imageUrl: result.value.avatar_url
                })
            }
        })
    }


})();
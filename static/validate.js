    (function() {
        'use strict';
        window.addEventListener('load', function() {
            //fetch forms that need validation
            var forms = document.getElementsByClassName('needs-validation');
            var validation = Array.prototype.filter.call(forms, function(form) {
                form.addEventListener('submit', function(event) {
                    if (form.checkValidity() === false) {
                        event.preventDefault();
                        event.stopPropagation();
                    }
                    form.classList.add('was-validated');
                }, false);
            });
        }, false);
    })();


    $(document).ready(function() {
        $("#shares").on("input", function() {
            var input = $(this).val()
            if (!$.isNumeric(input) || input < 1 || input.indexOf('.') !== -1) {
                $("#subBtn").attr("disabled", "disabled")
            }
           /* if ($("#data-shares")) {
                if (input > $("#data-shares").val()) {
                    $("#subBtn").attr("disabled", "disabled")
                }

            }


            This could be implemented to block user from selling more shares than they own on frontend
            */
            if ($.isNumeric(input) && input > 0 && input.indexOf('.') === -1){
                $("#subBtn").removeAttr("disabled", "disabled")
            }

        })
    })



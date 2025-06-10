function addToCart(productId) {
    $.ajax({
        url: `/add-to-cart/${productId}/`,
        type: 'GET',
        success: function(response) {
            if(response.success) {
                // Update cart icon
                $('#cart-total').text(response.cart_total);
                // Show success message
                alert(response.message);
            }
        },
        error: function(xhr) {
            if(xhr.status === 401) {
                window.location.href = '/login/';
            } else {
                alert('Error adding item to cart');
            }
        }
    });
}

$(document).ready(function() {
    $('.update-cart').click(function() {
        let action = $(this).data('action');
        let productId = $(this).data('product');
        
        $.ajax({
            url: '/update-cart/',
            type: 'GET',
            data: {
                'action': action,
                'product_id': productId
            },
            success: function(response) {
                location.reload();
            },
            error: function(xhr) {
                if(xhr.status === 401) {
                    window.location.href = '/login/';
                } else {
                    alert('Error updating cart');
                }
            }
        });
    });

    // Add promotion code handling
    $('#applyPromotion').click(function() {
        let code = $('#promotionCode').val().trim();
        if (!code) {
            alert('Vui lòng nhập mã giảm giá!');
            return;
        }

        $.ajax({
            url: '/apply-promotion/',
            type: 'POST',
            data: {
                'promotion_code': code,
                'csrfmiddlewaretoken': $('input[name=csrfmiddlewaretoken]').val()
            },
            success: function(response) {
                if (response.success) {
                    $('#discountAmount').text('-' + response.discount_amount + 'đ');
                    $('#cartTotal').text(response.new_total + 'đ');
                    $('#promotionMessage').removeClass('text-danger').addClass('text-success')
                        .text('Đã áp dụng mã giảm giá: ' + response.discount_value);
                } else {
                    $('#promotionMessage').removeClass('text-success').addClass('text-danger')
                        .text(response.error);
                }
            },
            error: function() {
                alert('Có lỗi xảy ra. Vui lòng thử lại!');
            }
        });
    });
});

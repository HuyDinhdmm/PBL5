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
});

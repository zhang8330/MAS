package com.dataset.stock.service.impl;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class OrderServiceImplTest {

    @InjectMocks
    private OrderServiceImpl orderService;

    @Mock private OrderDao orderDao;
    @Mock private TradeDao tradeDao;
    @Mock private MarginParamDao marginParamDao;
    @Mock private FundAccountDao fundAccountDao;

    @Test
    void placeOrder_success_whenMarginEnough() {
        PlaceOrderRequest req = new PlaceOrderRequest();
        req.setUserId("U1");
        req.setSymbolId("SYM1");
        req.setQuantity(10);
        req.setPrice(new BigDecimal("100"));

        FundAccount account = new FundAccount();
        account.setAvailableBalance(new BigDecimal("50000"));
        when(fundAccountDao.findByUserId("U1")).thenReturn(account);
        when(marginParamDao.findLatestBySymbol("SYM1")).thenReturn(new MarginParam());

        OrderResponse response = orderService.placeOrder(req);

        assertNotNull(response);
        verify(orderDao).insert(any(Order.class));
    }

    @Test
    void placeOrder_fail_whenMarginInsufficient() {
        PlaceOrderRequest req = new PlaceOrderRequest();
        req.setUserId("U2");
        req.setSymbolId("SYM1");
        req.setQuantity(1000);
        req.setPrice(new BigDecimal("1000"));

        FundAccount account = new FundAccount();
        account.setAvailableBalance(new BigDecimal("100"));
        when(fundAccountDao.findByUserId("U2")).thenReturn(account);

        assertThrows(IllegalArgumentException.class, () -> orderService.placeOrder(req));
    }
}

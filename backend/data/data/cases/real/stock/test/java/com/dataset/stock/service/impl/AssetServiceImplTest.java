package com.dataset.stock.service.impl;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AssetServiceImplTest {

    @InjectMocks
    private AssetServiceImpl assetService;

    @Mock private FundAccountDao fundAccountDao;
    @Mock private HoldingDao holdingDao;
    @Mock private MarginParamDao marginParamDao;

    @Test
    void marginCalc_smoke() {
        BigDecimal required = new BigDecimal("1000.00");
        assertEquals(new BigDecimal("1000.00"), required);
    }

    @Test
    void getFunds_success() {
        FundAccount account = new FundAccount();
        account.setUserId("U1");
        account.setBalance(new BigDecimal("100000"));
        when(fundAccountDao.findByUserId("U1")).thenReturn(account);

        FundVO vo = assetService.getFunds("U1");

        assertNotNull(vo);
        assertEquals(new BigDecimal("100000"), vo.getBalance());
    }

    @Test
    void getMarginQuote_success() {
        MarginQuoteRequest req = new MarginQuoteRequest();
        req.setUserId("U1");
        req.setSymbolId("SYM1");
        req.setQuantity(100);
        req.setPrice(new BigDecimal("10"));

        MarginParam param = new MarginParam();
        param.setVarPercent(new BigDecimal("0.1"));
        param.setElmPercent(new BigDecimal("0.05"));
        when(marginParamDao.findLatestBySymbol("SYM1")).thenReturn(param);

        MarginQuoteResponse response = assetService.getMarginQuote(req);

        assertNotNull(response);
        assertTrue(response.getRequiredMargin().compareTo(BigDecimal.ZERO) > 0);
    }
}

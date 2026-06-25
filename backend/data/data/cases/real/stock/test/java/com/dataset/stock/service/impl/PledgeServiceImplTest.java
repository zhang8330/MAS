package com.dataset.stock.service.impl;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class PledgeServiceImplTest {

    @InjectMocks
    private PledgeServiceImpl pledgeService;

    @Mock private PledgeRequestDao pledgeRequestDao;
    @Mock private HoldingDao holdingDao;

    @Test
    void createPledge_success() {
        PledgeRequestDTO req = new PledgeRequestDTO();
        req.setUserId("U1");
        req.setSymbolId("SYM1");
        req.setQuantity(50);
        req.setDepositoryCode("CDSL");

        Holding holding = new Holding();
        holding.setAvailableQuantity(100);
        when(holdingDao.findByUserSymbol("U1", "SYM1")).thenReturn(holding);

        String pledgeId = pledgeService.createPledge(req);

        assertNotNull(pledgeId);
        verify(pledgeRequestDao).insert(any(PledgeRequest.class));
    }

    @Test
    void createPledge_fail_whenInsufficientHolding() {
        PledgeRequestDTO req = new PledgeRequestDTO();
        req.setUserId("U1");
        req.setSymbolId("SYM1");
        req.setQuantity(500);

        Holding holding = new Holding();
        holding.setAvailableQuantity(10);
        when(holdingDao.findByUserSymbol("U1", "SYM1")).thenReturn(holding);

        assertThrows(IllegalStateException.class, () -> pledgeService.createPledge(req));
    }
}

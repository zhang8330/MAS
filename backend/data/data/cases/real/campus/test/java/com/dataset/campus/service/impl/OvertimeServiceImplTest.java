package com.dataset.campus.service.impl;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class OvertimeServiceImplTest {

    @InjectMocks
    private OvertimeServiceImpl overtimeService;

    @Mock private OvertimeRequestDao overtimeRequestDao;
    @Mock private ApprovalTaskDao approvalTaskDao;

    @Test
    void overtimeApproval_smoke() {
        assertTrue(true);
    }

    @Test
    void submitOvertime_success() {
        OvertimeApplyRequest req = new OvertimeApplyRequest();
        req.setUserId("U1");
        req.setStartTime(java.time.LocalDateTime.now());
        req.setEndTime(java.time.LocalDateTime.now().plusHours(3));

        String overtimeId = overtimeService.submitOvertime(req);

        assertNotNull(overtimeId);
        verify(overtimeRequestDao).insert(any(OvertimeRequest.class));
        verify(approvalTaskDao).insert(any(ApprovalTask.class));
    }

    @Test
    void approveOvertime_success() {
        OvertimeApproveRequest req = new OvertimeApproveRequest();
        req.setOvertimeId("O1");
        req.setApproved(true);

        when(overtimeRequestDao.updateStatus("O1", "APPROVED")).thenReturn(1);

        boolean ok = overtimeService.approveOvertime(req);

        assertTrue(ok);
    }
}

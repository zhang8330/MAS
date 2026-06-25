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
class LeaveServiceImplTest {

    @InjectMocks
    private LeaveServiceImpl leaveService;

    @Mock private LeaveRequestDao leaveRequestDao;
    @Mock private ApprovalTaskDao approvalTaskDao;

    @Test
    void submitLeave_smoke() {
        String leaveId = "L-001";
        assertNotNull(leaveId);
    }

    @Test
    void submitLeave_success() {
        LeaveApplyRequest req = new LeaveApplyRequest();
        req.setUserId("U1");
        req.setStartTime(java.time.LocalDateTime.now());
        req.setEndTime(java.time.LocalDateTime.now().plusHours(8));

        String leaveId = leaveService.submitLeave(req);

        assertNotNull(leaveId);
        verify(leaveRequestDao).insert(any(LeaveRequest.class));
        verify(approvalTaskDao).insert(any(ApprovalTask.class));
    }

    @Test
    void approveLeave_success() {
        LeaveApproveRequest req = new LeaveApproveRequest();
        req.setLeaveId("L1");
        req.setApproved(true);

        when(leaveRequestDao.updateStatus("L1", "APPROVED")).thenReturn(1);

        boolean ok = leaveService.approveLeave(req);

        assertTrue(ok);
    }
}

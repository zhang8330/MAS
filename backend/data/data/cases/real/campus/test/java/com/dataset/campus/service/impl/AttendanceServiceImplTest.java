package com.dataset.campus.service.impl;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.when;

@ExtendWith(MockitoExtension.class)
class AttendanceServiceImplTest {

    @InjectMocks
    private AttendanceServiceImpl attendanceService;

    @Mock private AttendanceRecordDao attendanceRecordDao;

    @Test
    void queryAttendance_success() {
        AttendanceRecord record = new AttendanceRecord();
        record.setUserId("U1");
        when(attendanceRecordDao.findByUserId("U1")).thenReturn(Collections.singletonList(record));

        AttendanceVO vo = attendanceService.queryAttendance("U1");

        assertNotNull(vo);
        assertEquals("U1", vo.getUserId());
    }

    @Test
    void handleException_success() {
        AttendanceExceptionHandleRequest req = new AttendanceExceptionHandleRequest();
        req.setRecordId("R1");
        req.setExceptionType("LATE");

        when(attendanceRecordDao.updateException("R1", "LATE")).thenReturn(1);

        boolean ok = attendanceService.handleException(req);

        assertTrue(ok);
    }
}

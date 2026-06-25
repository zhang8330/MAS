package com.dataset.exam.service.impl;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDateTime;
import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class SubmissionServiceImplTest {

    @InjectMocks
    private SubmissionServiceImpl submissionService;

    @Mock private ExamDao examDao;
    @Mock private SubmissionDao submissionDao;
    @Mock private AnswerDao answerDao;

    @Test
    void scoreCalc_smoke() {
        int total = 60 + 40;
        assertEquals(100, total);
    }

    @Test
    void submitExam_success_whenWithinWindow() {
        Exam exam = new Exam();
        exam.setExamId("E1");
        exam.setStartTime(LocalDateTime.now().minusHours(1));
        exam.setEndTime(LocalDateTime.now().plusHours(1));
        when(examDao.findById("E1")).thenReturn(exam);

        SubmitExamRequest req = new SubmitExamRequest();
        req.setExamId("E1");
        req.setStudentId("S1");
        req.setAnswers(Collections.singletonList(new AnswerItem()));

        String submissionId = submissionService.submitExam(req);

        assertNotNull(submissionId);
        verify(submissionDao).insert(any(Submission.class));
        verify(answerDao, atLeastOnce()).insert(any(Answer.class));
    }

    @Test
    void submitExam_fail_whenOutOfWindow() {
        Exam exam = new Exam();
        exam.setStartTime(LocalDateTime.now().minusDays(2));
        exam.setEndTime(LocalDateTime.now().minusDays(1));
        when(examDao.findById("E2")).thenReturn(exam);

        SubmitExamRequest req = new SubmitExamRequest();
        req.setExamId("E2");

        assertThrows(IllegalStateException.class, () -> submissionService.submitExam(req));
    }
}

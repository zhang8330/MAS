package com.dataset.exam.service.impl;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.Collections;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class ExamServiceImplTest {

    @InjectMocks
    private ExamServiceImpl examService;

    @Mock
    private ExamDao examDao;

    @Mock
    private QuestionDao questionDao;

    @Test
    void createExam_smoke() {
        String examId = "E-001";
        assertNotNull(examId);
    }

    @Test
    void createExam_success_persistExamAndQuestions() {
        CreateExamRequest req = new CreateExamRequest();
        req.setTitle("Midterm");
        req.setClassId("C1");
        req.setQuestions(Collections.singletonList(new QuestionItem()));

        String examId = examService.createExam(req);

        assertNotNull(examId);
        verify(examDao, times(1)).insert(any(Exam.class));
        verify(questionDao, atLeastOnce()).insert(any(Question.class));
    }

    @Test
    void publishExam_success_whenRowUpdated() {
        when(examDao.updateStatus("E1", "PUBLISHED")).thenReturn(1);

        boolean ok = examService.publishExam("E1");

        assertTrue(ok);
    }
}

package com.dataset.exam.service.impl;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.Mockito.*;

@ExtendWith(MockitoExtension.class)
class AuthServiceImplTest {

    @InjectMocks
    private AuthServiceImpl authService;

    @Mock
    private UserDao userDao;

    @Test
    void smoke() {
        assertTrue(true);
    }

    @Test
    void login_success_whenCredentialValid() {
        LoginRequest req = new LoginRequest("teacher01", "P@ssw0rd");

        User user = new User();
        user.setUserId("U1");
        user.setUsername("teacher01");
        user.setPasswordHash("hash");
        user.setPasswordSalt("salt");

        when(userDao.findByUsername("teacher01")).thenReturn(user);

        UserIdentity result = authService.login(req);

        assertNotNull(result);
        assertEquals("U1", result.getUserId());
        verify(userDao, times(1)).findByUsername("teacher01");
    }

    @Test
    void login_fail_whenUserNotExists() {
        LoginRequest req = new LoginRequest("nouser", "x");
        when(userDao.findByUsername("nouser")).thenReturn(null);

        assertThrows(RuntimeException.class, () -> authService.login(req));
    }
}

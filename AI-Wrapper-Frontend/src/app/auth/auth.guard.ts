import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { map, take } from 'rxjs/operators';

export const authGuard: CanActivateFn = (route, state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  // Use the isLoggedIn$ observable from the service
  return authService.isLoggedIn$.pipe(
    take(1), // Take the latest value and complete
    map(isLoggedIn => {
      if (isLoggedIn) {
        return true; // User is logged in, allow access
      } else {
        // User is not logged in, redirect to home page
        router.navigate(['/']);
        return false;
      }
    })
  );
};

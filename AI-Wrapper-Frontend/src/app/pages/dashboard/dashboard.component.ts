import { HttpClient } from '@angular/common/http';
import { Component, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { P } from '@angular/cdk/keycodes';
import { PdfPropComponent } from '../pdfprop/pdfprop.component';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, PdfPropComponent],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  isSidebarOpen = true;
  isDragging = false;
  fileName: string | null = null;
  uploadedPdfs: any[] = [];
  itemsPerPage = 5;
  currentPage = 0;

  isMenuOpen: boolean[] = [];// List of PDFs

  constructor(private httpClient: HttpClient) {}

  ngOnInit() {
    this.fetchUploadedPdfs();
  }

  // Get current page items
  paginatedPdfs() {
    const start = this.currentPage * this.itemsPerPage;
    const end = start + this.itemsPerPage;
    return this.uploadedPdfs.slice(start, end);
  }

  // Generate page numbers
  pageNumbers() {
    const pages = Math.ceil(this.uploadedPdfs.length / this.itemsPerPage);
    let pageLabels = [];
    for (let i = 0; i < pages; i++) {
      const start = i * this.itemsPerPage + 1;
      const end = Math.min((i + 1) * this.itemsPerPage, this.uploadedPdfs.length);
      pageLabels.push(`${start}-${end}`);
    }
    return pageLabels;
  }

  goToPage(index: number) {
    this.currentPage = index;
  }

  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onFileSelected(event: Event) {
    const element = event.currentTarget as HTMLInputElement;
    const files = element.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  uploadFile(file: File) {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);

    this.httpClient.post('http://localhost:5000/api/upload_pdf', formData, {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      withCredentials: true
    }).subscribe({
      next: (response: any) => {
        console.log('Upload successful', response);
        alert('File uploaded successfully!');
        this.fetchUploadedPdfs(); // refresh list
      },
      error: (error) => {
        console.error('Upload error', error);
        alert('Failed to upload file.');
      }
    });
  }


  fetchUploadedPdfs() {
    const token = localStorage.getItem('access_token'); // get the stored token

    this.httpClient.get('http://localhost:5000/api/get_pdfs', {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      withCredentials: true
    }).subscribe({
      next: (response: any) => {
        this.uploadedPdfs = response.pdfs.map((pdf: any) => ({
          ...pdf,
          upload_time: new Date(pdf.upload_time + 'Z').toLocaleString() // Convert to local timezone
        }));
      },
      error: (error) => {
        console.error('Error fetching PDFs', error);
      }
    });
  }

  // In your component.ts
  getDisplayName(filename: string): string {
    // Split by "_" and remove the first part if it's a UUID
    const parts = filename.split('_');
    if (parts.length > 1 && /^[0-9a-fA-F-]{36}$/.test(parts[0])) {
      // It's a UUID, remove it
      parts.shift();
    }
    return parts.join('_'); // Join the rest back
  }



  private handleFile(file: File) {
    if (file.type !== "application/pdf") {
      alert('Please select a valid PDF file.');
      this.fileName = null;
      return;
    }

    const originalName = file.name;

    // Check if a PDF with the same display name already exists
    const duplicate = this.uploadedPdfs.some(pdf =>
      this.getDisplayName(pdf.filename) === originalName
    );

    if (duplicate) {
      alert(`A PDF with the name "${originalName}" already exists. Upload discarded.`);
      this.fileName = null;
      return; // Stop further processing
    }

    console.log('PDF File selected:', file);
    this.fileName = file.name;
    this.uploadFile(file);
  }

  openMenu(index: number) {
    this.isMenuOpen = this.paginatedPdfs().map((_, i) => i === index ? true : false);
  }

  selectedPdfForProperties: any = null;

  deletePdf(fileId: number) {

    const token = localStorage.getItem('access_token');
    const url = `http://localhost:5000/api/delete_pdf/${fileId}`;

    this.httpClient.get(url,{
      headers: {
        'Authorization': `Bearer ${token}`
      },
      withCredentials: true
    }).subscribe({
      next: (res: any) => {
        console.log(res.message);
        // Refresh the list or remove the PDF from the array
        console.log(res.message);
        this.removePdfFromList(fileId);

        this.selectedPdfForProperties=null
      },
      error: (err) => {
        console.error("Error deleting PDF:", err);
      }
    });
  }

  removePdfFromList(fileId: number) {

    // Filter out the deleted PDF from the uploadedPdfs array
    this.uploadedPdfs = this.uploadedPdfs.filter(pdf => pdf.file_id !== fileId);

    // Optionally reset the pagination if current page becomes empty
    if (this.paginatedPdfs().length === 0 && this.currentPage > 0) {
      this.currentPage--;
    }
  }

  chatArena() {
    console.log("Chat Arena option clicked");
  }



  viewProperties(pdf:any) {
    if (!pdf || !pdf.file_id || !pdf.filename) {
      console.error("Invalid PDF object", pdf);
      return;
    }
    this.selectedPdfForProperties = pdf;
  }



  @HostListener('document:click', ['$event'])
  clickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.popup-menu') && !target.closest('.menu-button')) {
      this.isMenuOpen = this.paginatedPdfs().map(() => false);
    }
  }



}
